import React, { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Paper,
} from '@mui/material';
import {
  TrendingUp,
  QueryStats,
  People,
  Inventory,
  PlayArrow,
  Share,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { getMyAnalyses, getSharedAnalyses } from '../services/analytics';
import { Analysis, SharedAnalysis } from '../types';

interface DashboardStats {
  totalAnalyses: number;
  thisWeekAnalyses: number;
  sharedAnalyses: number;
  popularQueries: string[];
}

const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalAnalyses: 0,
    thisWeekAnalyses: 0,
    sharedAnalyses: 0,
    popularQueries: [],
  });
  const [recentAnalyses, setRecentAnalyses] = useState<Analysis[]>([]);
  const [popularShared, setPopularShared] = useState<SharedAnalysis[]>([]);
  const [loading, setLoading] = useState(true);

  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Fetch recent analyses
        const myAnalysesResponse = await getMyAnalyses(1, 5);
        setRecentAnalyses(myAnalysesResponse.analyses);

        // Fetch popular shared analyses
        const sharedResponse = await getSharedAnalyses(undefined, undefined, 1, 5);
        setPopularShared(sharedResponse.analyses);

        // Calculate stats
        setStats({
          totalAnalyses: myAnalysesResponse.total,
          thisWeekAnalyses: myAnalysesResponse.analyses.filter(
            (analysis) =>
              new Date(analysis.createdAt).getTime() >
              Date.now() - 7 * 24 * 60 * 60 * 1000
          ).length,
          sharedAnalyses: sharedResponse.total,
          popularQueries: [
            '매출 추이 분석',
            '고객 세그먼트 분석',
            '제품별 성과',
            '재고 현황',
            '예측 분석',
          ],
        });
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const quickActions = [
    {
      title: '새로운 분석',
      description: '자연어로 데이터를 분석하세요',
      icon: <QueryStats color="primary" />,
      action: () => navigate('/search'),
    },
    {
      title: '공유 분석 보기',
      description: '다른 사용자의 분석을 확인하세요',
      icon: <Share color="secondary" />,
      action: () => navigate('/shared'),
    },
  ];

  const statCards = [
    {
      title: '총 분석 수',
      value: stats.totalAnalyses,
      icon: <QueryStats />,
      color: '#1976d2',
    },
    {
      title: '이번 주 분석',
      value: stats.thisWeekAnalyses,
      icon: <TrendingUp />,
      color: '#2e7d32',
    },
    {
      title: '공유된 분석',
      value: stats.sharedAnalyses,
      icon: <People />,
      color: '#ed6c02',
    },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        대시보드
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        데이터 분석 현황을 한눈에 확인하세요
      </Typography>

      {/* Stats Cards */}
      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 4 }}>
        {statCards.map((stat, index) => (
          <Card key={index} sx={{ minWidth: 200, flex: 1 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    p: 1,
                    borderRadius: 1,
                    backgroundColor: stat.color,
                    color: 'white',
                  }}
                >
                  {stat.icon}
                </Box>
                <Box>
                  <Typography variant="h4">{stat.value}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {stat.title}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        {/* Quick Actions */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" gutterBottom>
            빠른 작업
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {quickActions.map((action, index) => (
              <Card key={index} sx={{ cursor: 'pointer' }} onClick={action.action}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    {action.icon}
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="h6">{action.title}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {action.description}
                      </Typography>
                    </Box>
                    <IconButton>
                      <PlayArrow />
                    </IconButton>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Box>

        {/* Recent Analyses */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" gutterBottom>
            최근 분석
          </Typography>
          <Paper>
            <List>
              {recentAnalyses.length > 0 ? (
                recentAnalyses.map((analysis) => (
                  <ListItem
                    key={analysis.id}
                    component="div"
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/analysis/${analysis.id}`)}
                  >
                    <ListItemIcon>
                      <QueryStats />
                    </ListItemIcon>
                    <ListItemText
                      primary={analysis.title || analysis.query}
                      secondary={new Date(analysis.createdAt).toLocaleDateString('ko-KR')}
                    />
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {analysis.tags?.slice(0, 2).map((tag) => (
                        <Chip key={tag} label={tag} size="small" />
                      ))}
                    </Box>
                  </ListItem>
                ))
              ) : (
                <ListItem>
                  <ListItemText
                    primary="아직 분석이 없습니다"
                    secondary="첫 번째 분석을 시작해보세요!"
                  />
                </ListItem>
              )}
            </List>
          </Paper>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' }, mt: 3 }}>
        {/* Popular Queries */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" gutterBottom>
            인기 질문
          </Typography>
          <Paper>
            <List>
              {stats.popularQueries.map((query, index) => (
                <ListItem
                  key={index}
                  component="div"
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/search?q=${encodeURIComponent(query)}`)}
                >
                  <ListItemIcon>
                    <TrendingUp />
                  </ListItemIcon>
                  <ListItemText primary={query} />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Box>

        {/* Popular Shared Analyses */}
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" gutterBottom>
            인기 공유 분석
          </Typography>
          <Paper>
            <List>
              {popularShared.length > 0 ? (
                popularShared.map((shared) => (
                  <ListItem
                    key={shared.id}
                    component="div"
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/shared/${shared.id}`)}
                  >
                    <ListItemIcon>
                      <Share />
                    </ListItemIcon>
                    <ListItemText
                      primary={`분석 by ${shared.sharedBy.name}`}
                      secondary={`사용 횟수: ${shared.usageCount} | 평점: ${shared.rating}/5`}
                    />
                  </ListItem>
                ))
              ) : (
                <ListItem>
                  <ListItemText
                    primary="공유된 분석이 없습니다"
                    secondary="다른 사용자들과 분석을 공유해보세요!"
                  />
                </ListItem>
              )}
            </List>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};

export default DashboardPage;