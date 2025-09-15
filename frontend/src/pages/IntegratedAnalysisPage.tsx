import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Alert,
  LinearProgress,
  CircularProgress,
  FormControlLabel,
  Switch,
  Slider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  IconButton,
  Divider,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  Psychology as AnalysisIcon,
  Assessment as ReportIcon,
  Visibility as ViewIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  Search as SearchIcon,
  AutoFixHigh as EnhanceIcon,
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

interface Dataset {
  id: string;
  name: string;
  description: string;
  collection: string;
  filters: any;
  data_count: number;
  created_at: string;
}

interface AnalysisResult {
  analysis_id: string;
  question: string;
  final_report: string;
  analysis_summary: {
    total_steps: number;
    final_score: number;
    execution_time: string;
    report_length: string;
  };
  reflection_history: any[];
  data_summary: string;
  created_at: string;
}

interface AnalysisStatus {
  analysis_id: string;
  status: 'starting' | 'data_loading' | 'analyzing' | 'completed' | 'failed';
  progress: number;
  current_step: number;
  total_steps: number;
  message: string;
  result?: AnalysisResult;
  error?: string;
}

const IntegratedAnalysisPage: React.FC = () => {
  // 탭 상태
  const [tabValue, setTabValue] = useState(0);

  // 데이터셋 관련 상태 (간소화)
  const [savedDatasets, setSavedDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);

  // 분석 관련 상태
  const [analysisQuestion, setAnalysisQuestion] = useState('');
  const [useReflection, setUseReflection] = useState(true);
  const [maxReflections, setMaxReflections] = useState(10);
  const [targetScore, setTargetScore] = useState(9.0);
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisStatus | null>(null);
  const [analysisHistory, setAnalysisHistory] = useState<AnalysisResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<AnalysisResult | null>(null);

  // UI 상태
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 추천 분석 질문
  const suggestedQuestions = [
    "고객 만족도가 낮은 제품들의 공통점과 개선 방안",
    "매출 상위 브랜드들의 성공 요인 분석",
    "고객 리뷰에서 발견되는 주요 불만사항과 해결책",
    "계절별 판매 패턴과 마케팅 전략 수립",
    "신규 고객 유치를 위한 효과적인 전략 도출",
  ];

  // 컴포넌트 마운트 시 초기화
  useEffect(() => {
    loadSavedDatasets();
    loadAnalysisHistory();
  }, []);

  // 현재 분석 상태 폴링
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (currentAnalysis && ['starting', 'data_loading', 'analyzing'].includes(currentAnalysis.status)) {
      interval = setInterval(() => {
        checkAnalysisStatus(currentAnalysis.analysis_id);
      }, 2000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentAnalysis]);

  const loadSavedDatasets = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/datasets/list`);
      setSavedDatasets(response.data.datasets || []);
    } catch (err) {
      console.error('데이터셋 목록 로드 실패:', err);
    }
  };

  const loadAnalysisHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/analysis/list`);
      const analyses = response.data.analyses || [];
      const completedAnalyses = analyses.filter((a: any) => a.status === 'completed');
      setAnalysisHistory(completedAnalyses);
    } catch (err) {
      console.error('분석 히스토리 로드 실패:', err);
    }
  };

  const startAnalysis = async () => {
    if (!analysisQuestion.trim()) {
      setError('분석 질문을 입력해주세요.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const request = {
        question: analysisQuestion.trim(),
        use_reflection: useReflection,
        max_reflections: maxReflections,
        target_score: targetScore,
        ...(selectedDataset && { dataset_id: selectedDataset.id }),
      };

      const response = await axios.post(`${API_BASE_URL}/analysis/advanced`, request);
      
      if (response.data.analysis_id) {
        setCurrentAnalysis({
          analysis_id: response.data.analysis_id,
          status: 'starting',
          progress: 0,
          current_step: 0,
          total_steps: maxReflections,
          message: '분석을 시작합니다...',
        });
        
        setTabValue(2); // 진행 상황 탭으로 이동
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '분석 시작에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const checkAnalysisStatus = async (analysisId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/analysis/status/${analysisId}`);
      const status: AnalysisStatus = response.data;
      
      setCurrentAnalysis(status);
      
      if (status.status === 'completed' && status.result) {
        setAnalysisHistory(prev => [status.result!, ...prev]);
        setSelectedResult(status.result!);
        setTabValue(3); // 결과 탭으로 이동
      } else if (status.status === 'failed') {
        setError(status.error || '분석에 실패했습니다.');
      }
    } catch (err) {
      console.error('상태 확인 실패:', err);
    }
  };

  const downloadReport = (result: AnalysisResult) => {
    const content = `
# ${result.question}

## 분석 요약
- 실행 시간: ${result.analysis_summary.execution_time}
- 최종 점수: ${result.analysis_summary.final_score}/10
- 총 단계: ${result.analysis_summary.total_steps}
- 보고서 길이: ${result.analysis_summary.report_length}

## 데이터 요약
${result.data_summary}

## 분석 보고서
${result.final_report}

---
생성 시간: ${new Date(result.created_at).toLocaleString()}
    `.trim();

    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis_${result.analysis_id}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <AnalysisIcon fontSize="large" />
        스마트 데이터 분석 플랫폼
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        MongoDB 데이터를 활용한 AI 분석과 예측으로 비즈니스 인사이트를 얻어보세요.
      </Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="데이터 분석" icon={<AnalysisIcon />} />
          <Tab label="예측 모델링" icon={<EnhanceIcon />} />
          <Tab label="진행 상황" icon={<PendingIcon />} disabled={!currentAnalysis} />
          <Tab label="결과 보기" icon={<ReportIcon />} disabled={!selectedResult} />
          <Tab label="히스토리" icon={<ViewIcon />} />
        </Tabs>
      </Box>

      {/* 데이터 분석 탭 */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                현황 분석 질문 입력
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                현재 데이터의 트렌드, 패턴, 인사이트를 분석합니다.
              </Typography>
              
              <TextField
                fullWidth
                multiline
                rows={4}
                value={analysisQuestion}
                onChange={(e) => setAnalysisQuestion(e.target.value)}
                placeholder="예: '최근 3개월 간 가장 인기 있는 브랜드는?', '고객 만족도가 낮은 제품들의 공통점은?'"
                sx={{ mb: 3 }}
              />

              <Typography variant="h6" gutterBottom>
                분석 옵션
              </Typography>
              
              <FormControlLabel
                control={
                  <Switch
                    checked={useReflection}
                    onChange={(e) => setUseReflection(e.target.checked)}
                  />
                }
                label="심층 분석 모드 (더 정확하고 상세한 분석)"
                sx={{ mb: 2 }}
              />

              {useReflection && (
                <Box sx={{ mb: 3 }}>
                  <Typography gutterBottom>
                    분석 반복 횟수: {maxReflections}회
                  </Typography>
                  <Slider
                    value={maxReflections}
                    onChange={(_, value) => setMaxReflections(value as number)}
                    min={1}
                    max={15}
                    marks
                    valueLabelDisplay="auto"
                    sx={{ mb: 2 }}
                  />
                  
                  <Typography gutterBottom>
                    목표 품질 점수: {targetScore}/10
                  </Typography>
                  <Slider
                    value={targetScore}
                    onChange={(_, value) => setTargetScore(value as number)}
                    min={7.0}
                    max={10.0}
                    step={0.1}
                    marks
                    valueLabelDisplay="auto"
                    sx={{ mb: 2 }}
                  />
                </Box>
              )}

              {savedDatasets.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    데이터셋 선택 (선택사항)
                  </Typography>
                  <FormControl fullWidth>
                    <InputLabel>저장된 데이터셋</InputLabel>
                    <Select
                      value={selectedDataset?.id || ''}
                      onChange={(e) => {
                        const dataset = savedDatasets.find(d => d.id === e.target.value);
                        setSelectedDataset(dataset || null);
                      }}
                    >
                      <MenuItem value="">자동 선택 (질문에 맞는 데이터 자동 탐지)</MenuItem>
                      {savedDatasets.map((dataset) => (
                        <MenuItem key={dataset.id} value={dataset.id}>
                          {dataset.name} ({dataset.data_count}개 레코드)
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
              )}

              <Alert severity="info" sx={{ mb: 3 }}>
                {selectedDataset 
                  ? `선택된 데이터: ${selectedDataset.name}` 
                  : '자동 데이터 선택: 질문 내용에 따라 최적의 데이터를 자동으로 선택합니다.'
                }
              </Alert>

              {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

              <Button
                variant="contained"
                size="large"
                onClick={startAnalysis}
                disabled={loading || !analysisQuestion.trim()}
                startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                fullWidth
              >
                {loading ? '분석 시작 중...' : '데이터 분석 시작'}
              </Button>

              <Alert severity="info" sx={{ mt: 2 }}>
                💡 분석에는 시간이 소요됩니다. 분석이 완료되면 알림을 드릴게요!
              </Alert>
              
              <Alert severity="success" sx={{ mt: 1 }}>
                📋 MongoDB 데이터: 8개 컴렉션 연결됨 (products, reviews, orders, buyers, sellers 등)
              </Alert>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                추천 분석 질문
              </Typography>
              <List>
                {suggestedQuestions.map((question, index) => (
                  <ListItem key={index} button onClick={() => setAnalysisQuestion(question)}>
                    <ListItemText primary={question} />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* 예측 모델링 탭 */}
      {tabValue === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                예측 목표 설정
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                미래 트렌드를 예측하고 비즈니스 전략을 수립합니다.
              </Typography>
              
              <TextField
                fullWidth
                multiline
                rows={4}
                value={analysisQuestion}
                onChange={(e) => setAnalysisQuestion(e.target.value)}
                placeholder="예: '다음 달 바이어 수요 예측', '신상품 출시 시 예상 매출', '고객 이탈 리스크 예측'"
                sx={{ mb: 3 }}
              />

              <Alert severity="warning" sx={{ mb: 2 }}>
                ⚠️ 예측 결과는 역사적 데이터에 기반한 예측이므로 참고용으로만 활용해주세요.
              </Alert>

              <Button
                variant="contained"
                size="large"
                onClick={startAnalysis}
                disabled={loading || !analysisQuestion.trim()}
                startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                fullWidth
                color="secondary"
              >
                {loading ? '예측 모델 학습 중...' : '예측 모델링 시작'}
              </Button>

              <Alert severity="info" sx={{ mt: 2 }}>
                🔮 예측 모델 학습에는 시간이 소요됩니다. 모델링이 완료되면 알림을 드릴게요!
              </Alert>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                예측 목표 예시
              </Typography>
              <List>
                {[
                  "다음 월 브랜드별 매출 예측",
                  "신상품 출시 시 예상 반응도",
                  "고객 이탈 리스크 예측",
                  "계절별 인기 카테고리 예측",
                  "재고 수요 예측 모델",
                ].map((question, index) => (
                  <ListItem key={index} button onClick={() => setAnalysisQuestion(question)}>
                    <ListItemText primary={question} />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* 진행 상황 탭 */}
      {tabValue === 2 && currentAnalysis && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            분석 진행 상황
          </Typography>
          
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2">{currentAnalysis.message}</Typography>
              <Typography variant="body2">{Math.round(currentAnalysis.progress)}%</Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={currentAnalysis.progress} 
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{currentAnalysis.current_step}</Typography>
                  <Typography variant="body2" color="text.secondary">현재 단계</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{currentAnalysis.total_steps}</Typography>
                  <Typography variant="body2" color="text.secondary">총 단계</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{currentAnalysis.status}</Typography>
                  <Typography variant="body2" color="text.secondary">상태</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{currentAnalysis.analysis_id.slice(-8)}</Typography>
                  <Typography variant="body2" color="text.secondary">분석 ID</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Button
            variant="outlined"
            onClick={() => checkAnalysisStatus(currentAnalysis.analysis_id)}
            startIcon={<RefreshIcon />}
          >
            상태 새로고침
          </Button>
        </Paper>
      )}

      {/* 결과 보기 탭 */}
      {tabValue === 3 && selectedResult && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6">분석 결과</Typography>
            <Button
              variant="outlined"
              onClick={() => downloadReport(selectedResult)}
              startIcon={<DownloadIcon />}
            >
              보고서 다운로드
            </Button>
          </Box>

          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{selectedResult.analysis_summary.final_score}/10</Typography>
                  <Typography variant="body2" color="text.secondary">최종 점수</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{selectedResult.analysis_summary.total_steps}</Typography>
                  <Typography variant="body2" color="text.secondary">총 반복 횟수</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{selectedResult.analysis_summary.execution_time}</Typography>
                  <Typography variant="body2" color="text.secondary">실행 시간</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{selectedResult.analysis_summary.report_length}</Typography>
                  <Typography variant="body2" color="text.secondary">보고서 길이</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">분석 보고서</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                  {selectedResult.final_report}
                </Typography>
              </Paper>
            </AccordionDetails>
          </Accordion>
        </Paper>
      )}

      {/* 히스토리 탭 */}
      {tabValue === 4 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            분석 히스토리
          </Typography>
          
          {analysisHistory.length === 0 ? (
            <Alert severity="info">아직 완료된 분석이 없습니다.</Alert>
          ) : (
            <List>
              {analysisHistory.map((result, index) => (
                <React.Fragment key={result.analysis_id}>
                  <ListItem 
                    button 
                    onClick={() => {
                      setSelectedResult(result);
                      setTabValue(3);
                    }}
                  >
                    <ListItemText
                      primary={result.question}
                      secondary={`${new Date(result.created_at).toLocaleString()} | 점수: ${result.analysis_summary.final_score}/10 | ${result.analysis_summary.execution_time}`}
                    />
                    <ListItemSecondaryAction>
                      <IconButton onClick={(e) => {
                        e.stopPropagation();
                        downloadReport(result);
                      }}>
                        <DownloadIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                  {index < analysisHistory.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          )}
        </Paper>
      )}
    </Container>
  );
};

export default IntegratedAnalysisPage;