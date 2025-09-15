import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Select,
  MenuItem,
  Switch,
  Slider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
} from '@mui/material';
import {
  Search,
  Save,
  Share,
  TrendingUp,
  Settings,
  ExpandMore,
  BarChart,
  ShowChart,
  DonutLarge,
  ScatterPlot,
  Psychology,
  Lightbulb,
} from '@mui/icons-material';
import { VegaEmbed } from 'react-vega';
import { useSearchParams } from 'react-router-dom';
import { submitQuery, saveAnalysis, getSharedAnalyses } from '../services/analytics';
import { AnalysisResult, SharedAnalysis } from '../types';
import naturalLanguageSearchService from '../services/naturalLanguageSearch';

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [sharedAnalyses, setSharedAnalyses] = useState<SharedAnalysis[]>([]);
  const [searchParams] = useSearchParams();
  const [aiMode, setAiMode] = useState<boolean>(false); // AI 모드 토글 상태 (기본값 false)
  const [queryExamples, setQueryExamples] = useState<string[]>([]);
  const [showExamples, setShowExamples] = useState(false);
  const [nlSearchResult, setNlSearchResult] = useState<any>(null);
  
  // 진행률 상태 추가
  const [analysisProgress, setAnalysisProgress] = useState<{
    step: string;
    progress: number;
    message: string;
  }>({
    step: '',
    progress: 0,
    message: ''
  });
  
  // 옵션 패널 상태
  const [chartType, setChartType] = useState<string>('bar');
  const [colorScheme, setColorScheme] = useState<string>('category10');
  const [showDataLabels, setShowDataLabels] = useState<boolean>(true);
  const [chartOpacity, setChartOpacity] = useState<number>(0.8);
  const [showGrid, setShowGrid] = useState<boolean>(true);

  const aiSampleQueries = [
    '일별 매출 추이를 보여줘',
    '제품별 매출 현황을 분석해줘',
    '다음 주 매출을 예측해줘',
    '고객 세그먼트를 분석해줘',
    '재고 현황을 보여줘',
    '이번 주 가장 많이 팔린 제품은?',
    '30대 여성 고객의 구매 패턴을 분석해줘',
  ];

  const simpleSampleQueries = [
    '리뷰 최신 10개',
    '상품 총합',
    '주문 20개',
    '고객 평균',
    '판매 최신',
    '리뷰',
    '상품 50개',
  ];

  const sampleQueries = aiMode ? aiSampleQueries : simpleSampleQueries;

  useEffect(() => {
    // 자연어 예시 가져오기
    const examples = naturalLanguageSearchService.getExamples();
    setQueryExamples(examples);
    
    const q = searchParams.get('q');
    if (q) {
      setQuery(q);
      handleSubmit(q);
    }

    // Load shared analyses
    loadSharedAnalyses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const loadSharedAnalyses = async () => {
    try {
      const response = await getSharedAnalyses(undefined, undefined, 1, 5);
      setSharedAnalyses(response.analyses);
    } catch (error) {
      console.error('Failed to load shared analyses:', error);
    }
  };

  const handleSubmit = async (queryText?: string) => {
    const searchQuery = queryText || query;
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setNlSearchResult(null);
    
    // 진행률 초기화 및 단계별 업데이트
    const updateProgress = (step: string, progress: number, message: string) => {
      setAnalysisProgress({ step, progress, message });
    };

    try {
      if (aiMode) {
        // AI 모드 ON: 기존 방식
        updateProgress('init', 10, '🤖 AI 모델을 준비하는 중...');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        updateProgress('parse', 30, '📝 자연어 쿼리를 분석하는 중...');
        await new Promise(resolve => setTimeout(resolve, 800));
        
        updateProgress('mongodb', 60, '🔍 MongoDB 쿼리를 생성하는 중...');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        updateProgress('execute', 80, '⚡ 데이터베이스에서 데이터를 조회하는 중...');
        
        const response = await submitQuery({ 
          query: searchQuery, 
          use_ai_mode: true 
        });
        
        updateProgress('insights', 95, '💡 AI가 인사이트를 생성하는 중...');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        updateProgress('complete', 100, '✅ 분석이 완료되었습니다!');
        
        setResult(response);

        if (response.error) {
          setError(response.error);
        }
      } else {
        // AI 모드 OFF: T5-small 모델 사용
        updateProgress('init', 20, '🔄 T5 모델을 준비하는 중...');
        await new Promise(resolve => setTimeout(resolve, 300));
        
        updateProgress('parse', 50, '📝 자연어를 MongoDB 쿼리로 변환하는 중...');
        
        const searchResponse = await naturalLanguageSearchService.search({
          query: searchQuery,
          ai_mode: false
        });
        
        updateProgress('execute', 80, '⚡ 데이터베이스에서 검색 중...');
        await new Promise(resolve => setTimeout(resolve, 300));
        
        updateProgress('complete', 100, '✅ 검색이 완료되었습니다!');
        
        setNlSearchResult(searchResponse);
        
        if (!searchResponse.success) {
          setError(searchResponse.error || '검색 중 오류가 발생했습니다.');
        }
      }
    } catch (err: any) {
      setError(err.message || '처리 중 오류가 발생했습니다.');
      updateProgress('error', 0, '❌ 분석 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
      // 완료 후 진행률 초기화
      setTimeout(() => {
        setAnalysisProgress({ step: '', progress: 0, message: '' });
      }, 2000);
    }
  };

  const handleSampleQuery = (sampleQuery: string) => {
    setQuery(sampleQuery);
    handleSubmit(sampleQuery);
  };

  const handleSaveAnalysis = async () => {
    if (!result) return;

    try {
      await saveAnalysis({
        query,
        result,
        title: title || query,
        description,
        tags,
        isPublic: false,
      });
      setSaveDialogOpen(false);
      setTitle('');
      setDescription('');
      setTags([]);
    } catch (error) {
      console.error('Failed to save analysis:', error);
    }
  };

  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  // 차트 타입에 따른 Vega-Lite 스펙 생성
  const generateVisualizationSpec = (originalSpec: any, type: string) => {
    if (!originalSpec || !originalSpec.data) return originalSpec;
    
    const baseSpec = {
      ...originalSpec,
      mark: getMarkByType(type),
      encoding: {
        ...originalSpec.encoding,
        opacity: showDataLabels ? { value: chartOpacity } : undefined,
      },
      config: {
        view: { strokeWidth: 0 },
        axis: { grid: showGrid },
        range: { category: { scheme: colorScheme } },
        mark: { tooltip: true }
      }
    };

    // 차트 타입별 인코딩 조정
    if (type === 'pie') {
      baseSpec.encoding = {
        theta: { field: '매출', type: 'quantitative' },
        color: { field: '날짜', type: 'nominal', scale: { scheme: colorScheme } }
      };
    } else if (type === 'scatter') {
      baseSpec.encoding = {
        x: { field: '날짜', type: 'ordinal' },
        y: { field: '매출', type: 'quantitative' },
        size: { value: 100 },
        color: { value: getColorByScheme(colorScheme) }
      };
    }

    return baseSpec;
  };

  const getMarkByType = (type: string) => {
    switch (type) {
      case 'bar': return { type: 'bar', opacity: chartOpacity };
      case 'line': return { type: 'line', point: true, strokeWidth: 3, opacity: chartOpacity };
      case 'area': return { type: 'area', opacity: chartOpacity };
      case 'pie': return { type: 'arc', innerRadius: 50, opacity: chartOpacity };
      case 'scatter': return { type: 'circle', size: 100, opacity: chartOpacity };
      default: return { type: 'bar', opacity: chartOpacity };
    }
  };

  const getColorByScheme = (scheme: string) => {
    const colors = {
      category10: '#1f77b4',
      category20: '#aec7e8',
      viridis: '#440154',
      plasma: '#0d0887',
      inferno: '#000004'
    };
    return colors[scheme as keyof typeof colors] || colors.category10;
  };

  const chartTypeOptions = [
    { value: 'bar', label: '막대 그래프', icon: <BarChart /> },
    { value: 'line', label: '선 그래프', icon: <ShowChart /> },
    { value: 'area', label: '면적 그래프', icon: <ShowChart /> },
    { value: 'pie', label: '원형 그래프', icon: <DonutLarge /> },
    { value: 'scatter', label: '산점도', icon: <ScatterPlot /> },
  ];

  const colorSchemeOptions = [
    { value: 'category10', label: '기본 색상' },
    { value: 'category20', label: '파스텔 색상' },
    { value: 'viridis', label: '비리디스' },
    { value: 'plasma', label: '플라즈마' },
    { value: 'inferno', label: '인페르노' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        자연어 검색
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        자연어로 질문하고 데이터 분석 결과를 확인하세요
      </Typography>

      {/* Search Form */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            fullWidth
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={aiMode ? "예: 이번 달 매출 추이를 보여줘" : "예: 이번 달 부정적인 리뷰를 출력해줘"}
            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
            disabled={loading}
          />
          <Button
            variant="contained"
            onClick={() => handleSubmit()}
            disabled={loading || !query.trim()}
            startIcon={loading ? <CircularProgress size={20} /> : <Search />}
          >
            {loading ? '처리 중...' : '검색'}
          </Button>
        </Box>

        {/* AI 모드 토글 */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={aiMode}
                  onChange={(e) => setAiMode(e.target.checked)}
                  color="primary"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Psychology color={aiMode ? "primary" : "disabled"} />
                  <Typography variant="body2">
                    AI 모드 {aiMode ? 'ON' : 'OFF'}
                  </Typography>
                </Box>
              }
            />
            <Tooltip title={aiMode ? "AI가 자연어를 분석하여 시각화와 인사이트를 제공합니다" : "T5 모델이 자연어를 MongoDB 쿼리로 변환하여 검색합니다"}>
              <IconButton size="small">
                <Lightbulb fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
          <Button
            size="small"
            variant="text"
            onClick={() => setShowExamples(!showExamples)}
          >
            예시 보기
          </Button>
        </Box>
        
        {/* 진행률 표시 */}
        {loading && analysisProgress.progress > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" color="primary" sx={{ mb: 1, fontWeight: 600 }}>
              {analysisProgress.message}
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={analysisProgress.progress} 
              sx={{ 
                height: 8, 
                borderRadius: 4,
                '& .MuiLinearProgress-bar': {
                  borderRadius: 4,
                }
              }} 
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              {analysisProgress.progress}% 완료
            </Typography>
          </Box>
        )}

        {/* 예시 검색어 */}
        {showExamples && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              예시 검색어:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {(aiMode ? sampleQueries : queryExamples).map((sq, index) => (
                <Chip
                  key={index}
                  label={sq}
                  onClick={() => handleSampleQuery(sq)}
                  clickable
                  size="small"
                  variant="outlined"
                  color={aiMode ? "primary" : "default"}
                />
              ))}
            </Box>
          </Box>
        )}
      </Paper>

      {/* 자연어 검색 결과 (AI 모드 OFF) */}
      {!aiMode && nlSearchResult && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            검색 결과
          </Typography>
          
          {/* 쿼리 변환 정보 */}
          {nlSearchResult.success && nlSearchResult.query && (
            <Accordion sx={{ mb: 2 }}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">🔍 변환된 MongoDB 쿼리</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ fontFamily: 'monospace', bgcolor: 'grey.100', p: 2, borderRadius: 1 }}>
                  <Typography variant="body2">
                    컬렉션: {nlSearchResult.query.collection}
                  </Typography>
                  <Typography variant="body2">
                    연산: {nlSearchResult.query.operation}
                  </Typography>
                  <Typography variant="body2">
                    필터: {JSON.stringify(nlSearchResult.query.filter, null, 2)}
                  </Typography>
                  {nlSearchResult.query.options && (
                    <Typography variant="body2">
                      옵션: {JSON.stringify(nlSearchResult.query.options, null, 2)}
                    </Typography>
                  )}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}
          
          {/* 결과 테이블 */}
          {nlSearchResult.results && nlSearchResult.results.length > 0 && (
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                📋 검색 결과: {nlSearchResult.results.length}개
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      {Object.keys(nlSearchResult.results[0]).filter(key => key !== '_id').slice(0, 5).map(key => (
                        <TableCell key={key}>{key}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {nlSearchResult.results.slice(0, 10).map((row: any, idx: number) => (
                      <TableRow key={idx}>
                        {Object.keys(row).filter(key => key !== '_id').slice(0, 5).map(key => (
                          <TableCell key={key}>
                            {typeof row[key] === 'object' ? JSON.stringify(row[key]) : String(row[key]).substring(0, 50)}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              {nlSearchResult.results.length > 10 && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  * 처음 10개 결과만 표시됩니다
                </Typography>
              )}
            </Box>
          )}
          
          {/* 오류 표시 */}
          {!nlSearchResult.success && (
            <Alert severity="error">
              {nlSearchResult.error || "검색 중 오류가 발생했습니다"}
            </Alert>
          )}
        </Paper>
      )}

      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        {/* Results */}
        <Box sx={{ flex: 2 }}>
          {/* 옵션 패널 (AI 모드에서만) */}
          {aiMode && result && (
            <Card sx={{ mb: 3 }}>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Settings />
                    <Typography variant="h6">시각화 옵션</Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                    {/* 차트 타입 선택 */}
                    <FormControl sx={{ minWidth: 200 }}>
                      <FormLabel component="legend">차트 종류</FormLabel>
                      <RadioGroup
                        value={chartType}
                        onChange={(e) => setChartType(e.target.value)}
                        row
                      >
                        {chartTypeOptions.map((option) => (
                          <FormControlLabel
                            key={option.value}
                            value={option.value}
                            control={<Radio />}
                            label={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {option.icon}
                                {option.label}
                              </Box>
                            }
                          />
                        ))}
                      </RadioGroup>
                    </FormControl>

                    {/* 색상 스킴 */}
                    <FormControl sx={{ minWidth: 150 }}>
                      <FormLabel>색상 테마</FormLabel>
                      <Select
                        value={colorScheme}
                        onChange={(e) => setColorScheme(e.target.value)}
                        size="small"
                      >
                        {colorSchemeOptions.map((option) => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    {/* 기타 옵션들 */}
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 250 }}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={showDataLabels}
                            onChange={(e) => setShowDataLabels(e.target.checked)}
                          />
                        }
                        label="데이터 라벨 표시"
                      />
                      
                      <FormControlLabel
                        control={
                          <Switch
                            checked={showGrid}
                            onChange={(e) => setShowGrid(e.target.checked)}
                          />
                        }
                        label="격자 표시"
                      />

                      <Box>
                        <Typography gutterBottom>투명도: {Math.round(chartOpacity * 100)}%</Typography>
                        <Slider
                          value={chartOpacity}
                          onChange={(_, value) => setChartOpacity(value as number)}
                          min={0.1}
                          max={1}
                          step={0.1}
                          size="small"
                        />
                      </Box>
                    </Box>
                  </Box>
                </AccordionDetails>
              </Accordion>
            </Card>
          )}
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {result && (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="h6">분석 결과</Typography>
                    {/* 처리 방식 표시 */}
                    <Chip 
                      label={aiMode ? "🧠 AI 모드" : "⚡ 단순 모드"}
                      size="small"
                      color={aiMode ? "primary" : "secondary"}
                      variant="outlined"
                    />
                  </Box>
                  <Box>
                    <IconButton onClick={() => setSaveDialogOpen(true)}>
                      <Save />
                    </IconButton>
                    <IconButton>
                      <Share />
                    </IconButton>
                  </Box>
                </Box>

                {result.model_status && (
                  <Chip
                    label={`${result.model_status.type} - ${result.model_status.status}`}
                    size="small"
                    color={result.model_status.status === 'ready' ? 'success' : 'default'}
                    sx={{ mb: 2 }}
                  />
                )}

                {result.visualization && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      시각화
                    </Typography>
                    <VegaEmbed 
                      spec={generateVisualizationSpec(result.visualization, chartType)} 
                      options={{ actions: false, tooltip: false }} 
                    />
                  </Box>
                )}

                {result.analysis && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      분석 결과
                    </Typography>
                    <Typography variant="body1">{result.analysis}</Typography>
                  </Box>
                )}

                {result.prediction_basis && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      예측 근거
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {result.prediction_basis}
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          )}
        </Box>

        {/* Sidebar */}
        <Box sx={{ flex: 1 }}>
          {/* Recent Shared Analyses */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <TrendingUp sx={{ mr: 1, verticalAlign: 'middle' }} />
                인기 공유 분석
              </Typography>
              <List dense>
                {sharedAnalyses.map((shared) => (
                  <ListItem key={shared.id} disablePadding>
                    <ListItemButton>
                      <ListItemText
                        primary={`분석 by ${shared.sharedBy.name}`}
                        secondary={`사용 횟수: ${shared.usageCount}`}
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* Save Analysis Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>분석 저장</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={query}
            sx={{ mb: 2, mt: 1 }}
          />
          <TextField
            fullWidth
            label="설명"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            multiline
            rows={3}
            sx={{ mb: 2 }}
          />
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
              <TextField
                size="small"
                label="태그 추가"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
              />
              <Button onClick={handleAddTag}>추가</Button>
            </Box>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {tags.map((tag) => (
                <Chip
                  key={tag}
                  label={tag}
                  onDelete={() => handleRemoveTag(tag)}
                  size="small"
                />
              ))}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)}>취소</Button>
          <Button onClick={handleSaveAnalysis} variant="contained">저장</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SearchPage;