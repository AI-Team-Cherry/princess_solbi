import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  TextField,
  InputAdornment,
  Tabs,
  Tab,
  Paper,
  Avatar,
  Divider,
  Button,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  QueryStats,
  Search,
  MoreVert,
  Delete,
  Edit,
  Share,
  Visibility,
  DateRange,
  TrendingUp,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { getMyAnalyses, deleteAnalysis, updateAnalysis } from '../services/analytics';
import { Analysis } from '../types';
import { useAuth } from '../contexts/AuthContext';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const MyPage: React.FC = () => {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [filteredAnalyses, setFilteredAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [tabValue, setTabValue] = useState(0);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);

  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadAnalyses();
  }, []);

  useEffect(() => {
    filterAnalyses();
  }, [analyses, searchQuery, tabValue]);

  const loadAnalyses = async () => {
    try {
      const response = await getMyAnalyses(1, 100); // Load all for now
      setAnalyses(response.analyses);
    } catch (error) {
      console.error('Failed to load analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterAnalyses = () => {
    let filtered = analyses;

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(
        (analysis) =>
          analysis.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (analysis.title && analysis.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (analysis.tags && analysis.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase())))
      );
    }

    // Filter by tab
    switch (tabValue) {
      case 1: // Recent
        filtered = filtered.filter(
          (analysis) =>
            new Date(analysis.createdAt).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000
        );
        break;
      case 2: // Shared
        filtered = filtered.filter((analysis) => analysis.isPublic);
        break;
    }

    setFilteredAnalyses(filtered);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, analysis: Analysis) => {
    setAnchorEl(event.currentTarget);
    setSelectedAnalysis(analysis);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedAnalysis(null);
  };

  const handleViewAnalysis = (analysis: Analysis) => {
    navigate(`/analysis/${analysis.id}`);
  };

  const handleDeleteAnalysis = async () => {
    if (selectedAnalysis) {
      try {
        await deleteAnalysis(selectedAnalysis.id);
        setAnalyses(analyses.filter((a) => a.id !== selectedAnalysis.id));
        handleMenuClose();
      } catch (error) {
        console.error('Failed to delete analysis:', error);
      }
    }
  };

  const handleShareToggle = async () => {
    if (selectedAnalysis) {
      try {
        await updateAnalysis(selectedAnalysis.id, {
          isPublic: !selectedAnalysis.isPublic,
        });
        setAnalyses(
          analyses.map((a) =>
            a.id === selectedAnalysis.id ? { ...a, isPublic: !a.isPublic } : a
          )
        );
        handleMenuClose();
      } catch (error) {
        console.error('Failed to update analysis:', error);
      }
    }
  };

  const getAnalysisStats = () => {
    const totalAnalyses = analyses.length;
    const recentAnalyses = analyses.filter(
      (analysis) =>
        new Date(analysis.createdAt).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000
    ).length;
    const sharedAnalyses = analyses.filter((analysis) => analysis.isPublic).length;

    return { totalAnalyses, recentAnalyses, sharedAnalyses };
  };

  const stats = getAnalysisStats();

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        마이페이지
      </Typography>

      {/* User Profile Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <Avatar sx={{ width: 80, height: 80, fontSize: '2rem' }}>
              {user?.name?.charAt(0)}
            </Avatar>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h5">{user?.name}</Typography>
              <Typography variant="body1" color="text.secondary">
                {user?.employeeId} | {user?.department}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                마지막 로그인: {user?.lastLogin ? new Date(user.lastLogin).toLocaleString('ko-KR') : '정보 없음'}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 2, maxWidth: 400 }}>
              <Paper sx={{ p: 2, textAlign: 'center', flex: 1 }}>
                <Typography variant="h6">{stats.totalAnalyses}</Typography>
                <Typography variant="caption">총 분석</Typography>
              </Paper>
              <Paper sx={{ p: 2, textAlign: 'center', flex: 1 }}>
                <Typography variant="h6">{stats.recentAnalyses}</Typography>
                <Typography variant="caption">최근 1주</Typography>
              </Paper>
              <Paper sx={{ p: 2, textAlign: 'center', flex: 1 }}>
                <Typography variant="h6">{stats.sharedAnalyses}</Typography>
                <Typography variant="caption">공유된 분석</Typography>
              </Paper>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Analyses Section */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">내 분석 목록</Typography>
            <TextField
              size="small"
              placeholder="분석 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </Box>

          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab label="전체" />
            <Tab label="최근 7일" />
            <Tab label="공유된 분석" />
          </Tabs>

          <TabPanel value={tabValue} index={0}>
            <AnalysisList
              analyses={filteredAnalyses}
              onView={handleViewAnalysis}
              onMenuOpen={handleMenuOpen}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <AnalysisList
              analyses={filteredAnalyses}
              onView={handleViewAnalysis}
              onMenuOpen={handleMenuOpen}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <AnalysisList
              analyses={filteredAnalyses}
              onView={handleViewAnalysis}
              onMenuOpen={handleMenuOpen}
            />
          </TabPanel>
        </CardContent>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleViewAnalysis(selectedAnalysis!)}>
          <ListItemIcon>
            <Visibility fontSize="small" />
          </ListItemIcon>
          상세 보기
        </MenuItem>
        <MenuItem onClick={handleShareToggle}>
          <ListItemIcon>
            <Share fontSize="small" />
          </ListItemIcon>
          {selectedAnalysis?.isPublic ? '공유 해제' : '공유하기'}
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleDeleteAnalysis}>
          <ListItemIcon>
            <Delete fontSize="small" />
          </ListItemIcon>
          삭제
        </MenuItem>
      </Menu>
    </Box>
  );
};

interface AnalysisListProps {
  analyses: Analysis[];
  onView: (analysis: Analysis) => void;
  onMenuOpen: (event: React.MouseEvent<HTMLElement>, analysis: Analysis) => void;
}

const AnalysisList: React.FC<AnalysisListProps> = ({ analyses, onView, onMenuOpen }) => {
  if (analyses.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body1" color="text.secondary">
          분석이 없습니다.
        </Typography>
        <Button variant="outlined" sx={{ mt: 2 }} href="/search">
          첫 번째 분석 시작하기
        </Button>
      </Box>
    );
  }

  return (
    <List>
      {analyses.map((analysis) => (
        <ListItem
          key={analysis.id}
          component="div"
          sx={{ border: 1, borderColor: 'divider', borderRadius: 1, mb: 1, cursor: 'pointer' }}
          onClick={() => onView(analysis)}
        >
          <ListItemIcon>
            <QueryStats />
          </ListItemIcon>
          <ListItemText
            primary={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {analysis.title || analysis.query}
                {analysis.isPublic && <Share fontSize="small" color="primary" />}
              </Box>
            }
            secondary={
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  {analysis.query.length > 100 ? `${analysis.query.substring(0, 100)}...` : analysis.query}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    <DateRange fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
                    {new Date(analysis.createdAt).toLocaleDateString('ko-KR')}
                  </Typography>
                  {analysis.tags?.map((tag) => (
                    <Chip key={tag} label={tag} size="small" />
                  ))}
                </Box>
              </Box>
            }
          />
          <ListItemSecondaryAction>
            <IconButton
              edge="end"
              onClick={(e) => {
                e.stopPropagation();
                onMenuOpen(e, analysis);
              }}
            >
              <MoreVert />
            </IconButton>
          </ListItemSecondaryAction>
        </ListItem>
      ))}
    </List>
  );
};

export default MyPage;