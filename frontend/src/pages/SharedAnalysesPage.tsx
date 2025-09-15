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
  Button,
  Avatar,
  Rating,
  Menu,
  MenuItem,
  Divider,
} from '@mui/material';
import {
  Search,
  Share,
  TrendingUp,
  Person,
  Visibility,
  ThumbUp,
  MoreVert,
  FilterList,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { getSharedAnalyses, applySharedAnalysis } from '../services/analytics';
import { SharedAnalysis } from '../types';

const SharedAnalysesPage: React.FC = () => {
  const [sharedAnalyses, setSharedAnalyses] = useState<SharedAnalysis[]>([]);
  const [filteredAnalyses, setFilteredAnalyses] = useState<SharedAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<SharedAnalysis | null>(null);

  const navigate = useNavigate();

  const categories = [
    { value: 'all', label: '전체' },
    { value: 'sales', label: '매출 분석' },
    { value: 'customer', label: '고객 분석' },
    { value: 'product', label: '제품 분석' },
    { value: 'prediction', label: '예측 분석' },
  ];

  useEffect(() => {
    loadSharedAnalyses();
  }, []);

  useEffect(() => {
    filterAnalyses();
  }, [sharedAnalyses, searchQuery, selectedCategory]);

  const loadSharedAnalyses = async () => {
    try {
      const response = await getSharedAnalyses(undefined, undefined, 1, 100);
      setSharedAnalyses(response.analyses);
    } catch (error) {
      console.error('Failed to load shared analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterAnalyses = () => {
    let filtered = sharedAnalyses;

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter((analysis) =>
        analysis.originalAnalysisId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        analysis.sharedBy.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        analysis.category.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((analysis) => analysis.category === selectedCategory);
    }

    // Sort by popularity (usage count and rating)
    filtered.sort((a, b) => {
      const scoreA = a.usageCount * 0.7 + a.rating * 0.3;
      const scoreB = b.usageCount * 0.7 + b.rating * 0.3;
      return scoreB - scoreA;
    });

    setFilteredAnalyses(filtered);
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, analysis: SharedAnalysis) => {
    setAnchorEl(event.currentTarget);
    setSelectedAnalysis(analysis);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedAnalysis(null);
  };

  const handleUseAnalysis = async (analysis: SharedAnalysis) => {
    try {
      const newAnalysis = await applySharedAnalysis(analysis.id);
      navigate(`/analysis/${newAnalysis.id}`);
    } catch (error) {
      console.error('Failed to use shared analysis:', error);
    }
  };

  const handleViewDetails = (analysis: SharedAnalysis) => {
    navigate(`/shared/${analysis.id}`);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        공유 분석
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        다른 사용자들이 공유한 분석을 확인하고 재활용하세요
      </Typography>

      {/* Search and Filter */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', md: 'row' }, alignItems: 'center' }}>
            <Box sx={{ flex: 2 }}>
              <TextField
                fullWidth
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
            <Box sx={{ minWidth: 200 }}>
              <TextField
                fullWidth
                select
                label="카테고리"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                SelectProps={{ native: true }}
              >
                {categories.map((category) => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </TextField>
            </Box>
            <Box>
              <Button
                variant="outlined"
                startIcon={<FilterList />}
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCategory('all');
                }}
              >
                초기화
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Popular Analyses */}
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <TrendingUp />
        인기 분석
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        {filteredAnalyses.slice(0, 3).map((analysis) => (
          <Box key={analysis.id} sx={{ minWidth: 300, flex: 1 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <Avatar>{analysis.sharedBy.name.charAt(0)}</Avatar>
                  <Box>
                    <Typography variant="subtitle1">{analysis.sharedBy.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {analysis.sharedBy.department}
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Rating value={analysis.rating} readOnly size="small" />
                  <Typography variant="caption">
                    ({analysis.rating}/5)
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  사용 횟수: {analysis.usageCount}회
                </Typography>
                <Chip label={analysis.category} size="small" sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={() => handleUseAnalysis(analysis)}
                  >
                    사용하기
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => handleViewDetails(analysis)}
                  >
                    상세보기
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Box>
        ))}
      </Box>

      {/* All Analyses List */}
      <Typography variant="h6" gutterBottom sx={{ mt: 4, mb: 2 }}>
        전체 분석 목록 ({filteredAnalyses.length}개)
      </Typography>

      <Card>
        <List>
          {filteredAnalyses.map((analysis) => (
            <React.Fragment key={analysis.id}>
              <ListItem>
                <ListItemIcon>
                  <Avatar>{analysis.sharedBy.name.charAt(0)}</Avatar>
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1">
                        {analysis.sharedBy.name}의 분석
                      </Typography>
                      <Chip label={analysis.category} size="small" />
                    </Box>
                  }
                  secondary={
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        {analysis.sharedBy.department} | 
                        공유일: {new Date(analysis.sharedAt).toLocaleDateString('ko-KR')}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1 }}>
                        <Rating value={analysis.rating} readOnly size="small" />
                        <Typography variant="caption">
                          사용 {analysis.usageCount}회
                        </Typography>
                      </Box>
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => handleUseAnalysis(analysis)}
                    >
                      사용하기
                    </Button>
                    <IconButton onClick={(e) => handleMenuOpen(e, analysis)}>
                      <MoreVert />
                    </IconButton>
                  </Box>
                </ListItemSecondaryAction>
              </ListItem>
              <Divider />
            </React.Fragment>
          ))}
        </List>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleViewDetails(selectedAnalysis!)}>
          <ListItemIcon>
            <Visibility fontSize="small" />
          </ListItemIcon>
          상세 보기
        </MenuItem>
        <MenuItem onClick={() => handleUseAnalysis(selectedAnalysis!)}>
          <ListItemIcon>
            <Share fontSize="small" />
          </ListItemIcon>
          사용하기
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default SharedAnalysesPage;