import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  IconButton,
  Divider,
  Avatar,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Rating,
} from '@mui/material';
import {
  ArrowBack,
  Share,
  Edit,
  Delete,
  Bookmark,
  ThumbUp,
  Download,
} from '@mui/icons-material';
import { VegaEmbed } from 'react-vega';
import { getAnalysisById, deleteAnalysis, updateAnalysis, saveAnalysis } from '../services/analytics';
import { Analysis } from '../types';
import { useAuth } from '../contexts/AuthContext';

const AnalysisDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  
  // Edit form states
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editTags, setEditTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');

  useEffect(() => {
    if (id) {
      loadAnalysis(id);
    }
  }, [id]);

  const loadAnalysis = async (analysisId: string) => {
    try {
      const data = await getAnalysisById(analysisId);
      setAnalysis(data);
      setEditTitle(data.title || data.query);
      setEditDescription(data.description || '');
      setEditTags(data.tags || []);
    } catch (err: any) {
      setError(err.message || '분석을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async () => {
    if (!analysis) return;

    try {
      const updatedAnalysis = await updateAnalysis(analysis.id, {
        title: editTitle,
        description: editDescription,
        tags: editTags,
      });
      setAnalysis(updatedAnalysis);
      setEditDialogOpen(false);
    } catch (error) {
      console.error('Failed to update analysis:', error);
    }
  };

  const handleDelete = async () => {
    if (!analysis) return;

    try {
      await deleteAnalysis(analysis.id);
      navigate('/mypage');
    } catch (error) {
      console.error('Failed to delete analysis:', error);
    }
  };

  const handleSaveCopy = async () => {
    if (!analysis) return;

    try {
      await saveAnalysis({
        query: analysis.query,
        result: analysis.result,
        title: `${analysis.title || analysis.query} (복사본)`,
        description: analysis.description,
        tags: analysis.tags,
        isPublic: false,
      });
      setSaveDialogOpen(false);
      navigate('/mypage');
    } catch (error) {
      console.error('Failed to save copy:', error);
    }
  };

  const handleAddTag = () => {
    if (newTag.trim() && !editTags.includes(newTag.trim())) {
      setEditTags([...editTags, newTag.trim()]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditTags(editTags.filter(tag => tag !== tagToRemove));
  };

  const isOwner = analysis && user && analysis.userId === user.id;

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !analysis) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || '분석을 찾을 수 없습니다.'}
        </Alert>
        <Button variant="outlined" onClick={() => navigate(-1)}>
          돌아가기
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={() => navigate(-1)} sx={{ mr: 2 }}>
          <ArrowBack />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4">
            {analysis.title || analysis.query}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            생성일: {new Date(analysis.createdAt).toLocaleString('ko-KR')}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {!isOwner && (
            <Button
              variant="outlined"
              startIcon={<Bookmark />}
              onClick={() => setSaveDialogOpen(true)}
            >
              내 분석으로 저장
            </Button>
          )}
          {isOwner && (
            <>
              <IconButton onClick={() => setEditDialogOpen(true)}>
                <Edit />
              </IconButton>
              <IconButton onClick={() => setDeleteDialogOpen(true)}>
                <Delete />
              </IconButton>
            </>
          )}
          <IconButton>
            <Share />
          </IconButton>
        </Box>
      </Box>

      {/* Analysis Content */}
      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        <Box sx={{ flex: 2 }}>
          {/* Query */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                질문
              </Typography>
              <Typography variant="body1" sx={{ fontStyle: 'italic' }}>
                "{analysis.query}"
              </Typography>
            </CardContent>
          </Card>

          {/* Visualization */}
          {analysis.result.visualization && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  시각화 결과
                </Typography>
                <Box sx={{ width: '100%', overflow: 'auto' }}>
                  <VegaEmbed spec={analysis.result.visualization} options={{ actions: false, tooltip: false }} />
                </Box>
              </CardContent>
            </Card>
          )}

          {/* Analysis Result */}
          {analysis.result.analysis && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  분석 결과
                </Typography>
                <Typography variant="body1">
                  {analysis.result.analysis}
                </Typography>
              </CardContent>
            </Card>
          )}

          {/* Prediction Basis */}
          {analysis.result.prediction_basis && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  예측 근거
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {analysis.result.prediction_basis}
                </Typography>
              </CardContent>
            </Card>
          )}
        </Box>

        {/* Sidebar */}
        <Box sx={{ flex: 1 }}>
          {/* Metadata */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                분석 정보
              </Typography>
              
              {analysis.description && (
                <>
                  <Typography variant="subtitle2" gutterBottom>
                    설명
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {analysis.description}
                  </Typography>
                </>
              )}

              <Typography variant="subtitle2" gutterBottom>
                태그
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {analysis.tags && analysis.tags.length > 0 ? (
                  analysis.tags.map((tag) => (
                    <Chip key={tag} label={tag} size="small" />
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    태그가 없습니다.
                  </Typography>
                )}
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle2" gutterBottom>
                모델 정보
              </Typography>
              {analysis.result.model_status && (
                <Chip
                  label={`${analysis.result.model_status.type} - ${analysis.result.model_status.status}`}
                  size="small"
                  color={analysis.result.model_status.status === 'ready' ? 'success' : 'default'}
                />
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                작업
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button variant="outlined" startIcon={<Download />}>
                  결과 내보내기
                </Button>
                <Button variant="outlined" startIcon={<Share />}>
                  링크 공유
                </Button>
                {!isOwner && (
                  <Button 
                    variant="outlined" 
                    startIcon={<ThumbUp />}
                  >
                    유용해요
                  </Button>
                )}
              </Box>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>분석 수정</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="제목"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            sx={{ mb: 2, mt: 1 }}
          />
          <TextField
            fullWidth
            label="설명"
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
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
              {editTags.map((tag) => (
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
          <Button onClick={() => setEditDialogOpen(false)}>취소</Button>
          <Button onClick={handleEdit} variant="contained">저장</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>분석 삭제</DialogTitle>
        <DialogContent>
          <Typography>
            정말로 이 분석을 삭제하시겠습니까? 이 작업은 취소할 수 없습니다.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>취소</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            삭제
          </Button>
        </DialogActions>
      </Dialog>

      {/* Save Copy Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)}>
        <DialogTitle>내 분석으로 저장</DialogTitle>
        <DialogContent>
          <Typography>
            이 분석을 내 분석 목록에 복사본으로 저장하시겠습니까?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)}>취소</Button>
          <Button onClick={handleSaveCopy} variant="contained">
            저장
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AnalysisDetailPage;