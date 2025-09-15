import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Chip,
  Alert,
  CircularProgress,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import { Grid } from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Psychology as PsychologyIcon,
  TrendingUp as TrendingUpIcon,
  ScatterPlot as ScatterPlotIcon,
  Timeline as TimelineIcon,
  Warning as WarningIcon,
  InfoOutlined as InfoIcon,
} from '@mui/icons-material';
import { VegaEmbed } from 'react-vega';
import { 
  mlAnalyticsService, 
  MLMethod, 
  MLCollection, 
  MLAnalysisResult 
} from '../services/mlAnalytics';

const MLAnalyticsPage: React.FC = () => {
  // 상태 관리
  const [methods, setMethods] = useState<Record<string, MLMethod>>({});
  const [collections, setCollections] = useState<MLCollection[]>([]);
  const [selectedMethod, setSelectedMethod] = useState<string>('');
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MLAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMethods, setLoadingMethods] = useState(true);
  const [loadingCollections, setLoadingCollections] = useState(true);
  
  // 알림 관련 상태 추가
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>('default');
  const [analysisStartTime, setAnalysisStartTime] = useState<Date | null>(null);
  
  // 분석 취소를 위한 AbortController
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  
  // 최근 분석 히스토리
  const [analysisHistory, setAnalysisHistory] = useState<Array<{
    method: string;
    collection: string;
    startTime: Date;
    endTime: Date;
    duration: number;
    success: boolean;
  }>>([]);

  // 초기 데이터 로드
  useEffect(() => {
    const initializeData = async () => {
      try {
        // ML 방법 목록 로드
        const methodsData = await mlAnalyticsService.getMLMethods();
        setMethods(methodsData);
        setLoadingMethods(false);

        // ML 컬렉션 목록 로드
        const collectionsData = await mlAnalyticsService.getMLCollections();
        setCollections(collectionsData);
        setLoadingCollections(false);
      } catch (err: any) {
        setError(err.message);
        setLoadingMethods(false);
        setLoadingCollections(false);
      }
    };

    initializeData();
    
    // 알림 권한 요청
    const requestNotificationPermission = async () => {
      if ('Notification' in window) {
        const permission = await Notification.requestPermission();
        setNotificationPermission(permission);
      }
    };
    
    requestNotificationPermission();
  }, []);
  
  // 분석 완료 알림 함수
  const sendCompletionNotification = (method: string, duration: number) => {
    if ('Notification' in window && notificationPermission === 'granted') {
      new Notification('🧠 ML 분석 완료!', {
        body: `${method} 분석이 완료되었습니다. (소요시간: ${Math.round(duration / 1000)}초)`,
        icon: '/favicon.ico',
        tag: 'ml-analysis-complete',
        requireInteraction: true
      });
    }
    
    // 소리 알림 재생
    playNotificationSound();
  };
  
  // 알림 소리 재생 함수
  const playNotificationSound = () => {
    try {
      // Web Audio API를 사용해서 완료 사운드 생성
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // 성공 사운드 (상승하는 톤)
      oscillator.frequency.setValueAtTime(523, audioContext.currentTime); // C5
      oscillator.frequency.setValueAtTime(659, audioContext.currentTime + 0.1); // E5
      oscillator.frequency.setValueAtTime(784, audioContext.currentTime + 0.2); // G5
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
      console.log('알림 소리 재생 실패:', error);
    }
  };
  
  // 분석 취소 함수
  const handleCancelAnalysis = () => {
    if (abortController) {
      abortController.abort();
      setIsLoading(false);
      setError('분석이 사용자에 의해 취소되었습니다.');
      setAbortController(null);
      setAnalysisStartTime(null);
    }
  };

  // 분석 방법 변경 시 추천 매개변수 설정
  useEffect(() => {
    if (selectedMethod && selectedCollection) {
      const collection = collections.find(c => c.name === selectedCollection);
      if (collection) {
        const recommended = mlAnalyticsService.getRecommendedParameters(selectedMethod, collection);
        setParameters(recommended);
      }
    }
  }, [selectedMethod, selectedCollection, collections]);

  // 매개변수 변경 핸들러
  const handleParameterChange = (key: string, value: any) => {
    setParameters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // ML 분석 실행
  const handleRunAnalysis = async () => {
    if (!selectedMethod || !selectedCollection) {
      setError('분석 방법과 컬렉션을 선택해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);
    
    // 분석 시작 시간 기록 및 AbortController 생성
    const startTime = new Date();
    setAnalysisStartTime(startTime);
    const controller = new AbortController();
    setAbortController(controller);

    try {
      const analysisResult = await mlAnalyticsService.performAnalysis({
        analysis_type: selectedMethod as any,
        collection_name: selectedCollection,
        parameters,
        save_analysis: true,
        tags: ['ML', selectedMethod],
      });

      setResult(analysisResult);
      
      // 분석 완료 알림
      const endTime = new Date();
      const duration = endTime.getTime() - startTime.getTime();
      const methodName = methods[selectedMethod]?.name || selectedMethod;
      
      // 분석 히스토리에 추가
      const historyEntry = {
        method: methodName,
        collection: selectedCollection,
        startTime,
        endTime,
        duration,
        success: true
      };
      setAnalysisHistory(prev => [historyEntry, ...prev.slice(0, 4)]); // 최대 5개 보관
      
      // 브라우저 알림 전송
      sendCompletionNotification(methodName, duration);
      
      // 페이지가 백그라운드에 있을 때 탭 제목 변경
      if (document.hidden) {
        document.title = '🎉 ML 분석 완료! - NLP Analytics Platform';
        
        // 페이지가 다시 포커스될 때 원래 제목으로 복원
        const restoreTitle = () => {
          document.title = 'NLP Analytics Platform';
          document.removeEventListener('visibilitychange', restoreTitle);
        };
        document.addEventListener('visibilitychange', restoreTitle);
      }
      
    } catch (err: any) {
      setError(err.message);
      
      // 오류 발생 시에도 알림
      if (notificationPermission === 'granted') {
        new Notification('❌ ML 분석 실패', {
          body: `분석 중 오류가 발생했습니다: ${err.message}`,
          icon: '/favicon.ico',
          tag: 'ml-analysis-error'
        });
      }
    } finally {
      setIsLoading(false);
      setAnalysisStartTime(null);
      setAbortController(null);
    }
  };

  // 분석 아이콘 가져오기
  const getAnalysisIcon = (type: string) => {
    switch (type) {
      case 'clustering':
        return <ScatterPlotIcon />;
      case 'prediction':
        return <TrendingUpIcon />;
      case 'timeseries':
        return <TimelineIcon />;
      case 'anomaly':
        return <WarningIcon />;
      default:
        return <PsychologyIcon />;
    }
  };

  // 매개변수 입력 필드 렌더링
  const renderParameterField = (key: string, paramInfo: any) => {
    switch (paramInfo.type) {
      case 'int':
        return (
          <TextField
            key={key}
            label={key}
            type="number"
            value={parameters[key] || paramInfo.default || ''}
            onChange={(e) => handleParameterChange(key, parseInt(e.target.value) || paramInfo.default)}
            helperText={paramInfo.description}
            fullWidth
            margin="normal"
          />
        );
      case 'str':
        if (paramInfo.options) {
          return (
            <FormControl key={key} fullWidth margin="normal">
              <InputLabel>{key}</InputLabel>
              <Select
                value={parameters[key] || paramInfo.default || ''}
                onChange={(e) => handleParameterChange(key, e.target.value)}
              >
                {paramInfo.options.map((option: string) => (
                  <MenuItem key={option} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          );
        } else {
          return (
            <TextField
              key={key}
              label={key}
              value={parameters[key] || paramInfo.default || ''}
              onChange={(e) => handleParameterChange(key, e.target.value)}
              helperText={paramInfo.description}
              fullWidth
              margin="normal"
            />
          );
        }
      default:
        return null;
    }
  };

  if (loadingMethods || loadingCollections) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="h6" ml={2}>
          ML 분석 환경을 준비하는 중...
        </Typography>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        🧠 머신러닝 고급 분석
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" paragraph>
        scikit-learn과 k-means 클러스터링을 포함한 고급 머신러닝 기법으로 데이터를 분석합니다.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* 분석 설정 패널 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                📊 분석 설정
              </Typography>

              {/* 분석 방법 선택 */}
              <FormControl fullWidth margin="normal">
                <InputLabel>분석 방법</InputLabel>
                <Select
                  value={selectedMethod}
                  onChange={(e) => setSelectedMethod(e.target.value)}
                >
                  {Object.entries(methods).map(([key, method]) => (
                    <MenuItem key={key} value={key}>
                      <Box display="flex" alignItems="center">
                        {getAnalysisIcon(key)}
                        <Box ml={1}>
                          <Typography variant="body1">{method.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {method.description}
                          </Typography>
                        </Box>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* 컬렉션 선택 */}
              <FormControl fullWidth margin="normal">
                <InputLabel>데이터 컬렉션</InputLabel>
                <Select
                  value={selectedCollection}
                  onChange={(e) => setSelectedCollection(e.target.value)}
                >
                  {collections.map((collection) => (
                    <MenuItem key={collection.name} value={collection.name}>
                      <Box>
                        <Typography variant="body1">{collection.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {collection.document_count.toLocaleString()}개 문서, {collection.numeric_fields.length}개 수치 필드
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* 매개변수 설정 */}
              {selectedMethod && methods[selectedMethod] && (
                <Accordion sx={{ mt: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle1">고급 매개변수</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {Object.entries(methods[selectedMethod].parameters).map(([key, paramInfo]) =>
                      renderParameterField(key, paramInfo)
                    )}
                  </AccordionDetails>
                </Accordion>
              )}

              {/* 실행 버튼 */}
              <Button
                variant="contained"
                color="primary"
                fullWidth
                size="large"
                onClick={handleRunAnalysis}
                disabled={!selectedMethod || !selectedCollection || isLoading}
                sx={{ mt: 3 }}
              >
                {isLoading ? (
                  <>
                    <CircularProgress size={20} sx={{ mr: 1 }} />
                    분석 실행 중...
                  </>
                ) : (
                  '🚀 ML 분석 실행'
                )}
              </Button>
              
              {/* 진행률 및 분석 상태 표시 */}
              {isLoading && analysisStartTime && (
                <Box sx={{ mt: 2, p: 2, bgcolor: 'primary.50', borderRadius: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="body2" color="primary" sx={{ fontWeight: 600 }}>
                      🧠 ML 분석이 진행 중입니다...
                    </Typography>
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      onClick={handleCancelAnalysis}
                      startIcon={<span>⏹️</span>}
                    >
                      취소
                    </Button>
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                    시작 시간: {analysisStartTime.toLocaleTimeString()}
                  </Typography>
                  <LinearProgress sx={{ borderRadius: 1 }} />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    💡 분석이 완료되면 알림으로 알려드립니다!
                  </Typography>
                </Box>
              )}
              
              {/* 알림 권한 안내 */}
              {notificationPermission !== 'granted' && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    🔔 분석 완료 알림을 받으려면 브라우저 알림 권한을 허용해주세요.
                  </Typography>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* 컬렉션 정보 */}
          {selectedCollection && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  📋 선택된 컬렉션 정보
                </Typography>
                {(() => {
                  const collection = collections.find(c => c.name === selectedCollection);
                  if (!collection) return null;
                  
                  return (
                    <Box>
                      <Typography variant="body2" gutterBottom>
                        <strong>문서 수:</strong> {collection.document_count.toLocaleString()}개
                      </Typography>
                      <Typography variant="body2" gutterBottom>
                        <strong>수치 필드:</strong>
                      </Typography>
                      <Box sx={{ mb: 1 }}>
                        {collection.numeric_fields.map((field) => (
                          <Chip key={field} label={field} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                        ))}
                      </Box>
                      <Typography variant="body2" gutterBottom>
                        <strong>샘플 필드:</strong>
                      </Typography>
                      <Box>
                        {collection.sample_fields.map((field) => (
                          <Chip key={field} label={field} variant="outlined" size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                        ))}
                      </Box>
                    </Box>
                  );
                })()}
              </CardContent>
            </Card>
          )}
          
          {/* 분석 히스토리 */}
          {analysisHistory.length > 0 && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  📊 최근 분석 기록
                </Typography>
                <List dense>
                  {analysisHistory.map((entry, index) => (
                    <ListItem key={index} divider={index < analysisHistory.length - 1}>
                      <ListItemIcon>
                        {entry.success ? '✅' : '❌'}
                      </ListItemIcon>
                      <ListItemText
                        primary={`${entry.method} - ${entry.collection}`}
                        secondary={`${entry.startTime.toLocaleString()} (${Math.round(entry.duration / 1000)}초)`}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          )}
        </Grid>

        {/* 분석 결과 패널 */}
        <Grid item xs={12} md={6}>
          {result ? (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  📈 분석 결과
                </Typography>

                {/* 요약 정보 */}
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'primary.50' }}>
                  <Box display="flex" alignItems="center" mb={1}>
                    {getAnalysisIcon(result.analysis_type)}
                    <Typography variant="subtitle1" ml={1}>
                      {methods[result.analysis_type]?.name || result.analysis_type}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {mlAnalyticsService.interpretResult(result).summary}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    분석 데이터: {result.data_count.toLocaleString()}개 | {new Date(result.created_at).toLocaleString()}
                  </Typography>
                </Paper>

                {/* 시각화 */}
                {result.visualizations && result.visualizations.length > 0 && (
                  <Box mb={2}>
                    {result.visualizations.map((viz, index) => (
                      <Paper key={index} sx={{ p: 2, mb: 2 }}>
                        <VegaEmbed spec={viz} options={{ actions: false, tooltip: false }} />
                      </Paper>
                    ))}
                  </Box>
                )}

                {/* 인사이트 */}
                {result.ml_result.insights && result.ml_result.insights.length > 0 && (
                  <Accordion defaultExpanded>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1">💡 주요 인사이트</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <List>
                        {result.ml_result.insights.map((insight: string, index: number) => (
                          <ListItem key={index}>
                            <ListItemIcon>
                              <InfoIcon color="primary" />
                            </ListItemIcon>
                            <ListItemText primary={insight} />
                          </ListItem>
                        ))}
                      </List>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* 추천사항 */}
                {result.ml_result.recommendations && result.ml_result.recommendations.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle1">🎯 추천사항</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <List>
                        {result.ml_result.recommendations.map((recommendation: string, index: number) => (
                          <ListItem key={index}>
                            <ListItemIcon>
                              <TrendingUpIcon color="success" />
                            </ListItemIcon>
                            <ListItemText primary={recommendation} />
                          </ListItem>
                        ))}
                      </List>
                    </AccordionDetails>
                  </Accordion>
                )}

                {/* 상세 결과 */}
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle1">🔍 상세 결과</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <pre style={{ 
                      background: '#f5f5f5', 
                      padding: '16px', 
                      borderRadius: '4px',
                      fontSize: '12px',
                      overflow: 'auto',
                      maxHeight: '300px'
                    }}>
                      {JSON.stringify(result.ml_result, null, 2)}
                    </pre>
                  </AccordionDetails>
                </Accordion>
              </CardContent>
            </Card>
          ) : (
            <Paper sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
              <PsychologyIcon sx={{ fontSize: 48, mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                ML 분석 준비됨
              </Typography>
              <Typography variant="body2">
                분석 방법과 데이터 컬렉션을 선택한 후 분석을 실행하세요.
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>

      {/* 도움말 */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            🤔 ML 분석 가이드
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Box display="flex" alignItems="center" mb={1}>
                <ScatterPlotIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2">클러스터링</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                고객을 유사한 특성별로 그룹화하여 세분화된 마케팅 전략을 수립합니다.
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box display="flex" alignItems="center" mb={1}>
                <TrendingUpIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2">매출 예측</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                과거 데이터를 바탕으로 미래 매출을 예측하여 비즈니스 계획을 세웁니다.
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box display="flex" alignItems="center" mb={1}>
                <TimelineIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2">시계열 분석</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                시간에 따른 데이터 변화 패턴을 분석하여 트렌드와 계절성을 파악합니다.
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box display="flex" alignItems="center" mb={1}>
                <WarningIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2">이상치 탐지</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                정상 패턴에서 벗어난 데이터를 찾아 문제나 기회를 발견합니다.
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default MLAnalyticsPage;