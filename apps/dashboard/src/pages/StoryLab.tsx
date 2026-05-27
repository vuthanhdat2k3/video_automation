import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getStory, generateStory, regenerateStory, materializeStory, getProject } from '../api/endpoints';
import { useState, useEffect } from 'react';

export default function StoryLab() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  
  const [concept, setConcept] = useState('');
  const [showRegenForm, setShowRegenForm] = useState(false);

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  });

  const { data: bible, isLoading, isError } = useQuery({
    queryKey: ['story', id],
    queryFn: () => getStory(id!),
    enabled: !!id,
    retry: false,
  });

  useEffect(() => {
    if (bible?.series_overview) {
      setConcept(bible.series_overview);
    }
  }, [bible]);

  const genMut = useMutation({
    mutationFn: (data: any) => generateStory(id!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['story', id] });
    },
  });

  const regenMut = useMutation({
    mutationFn: (data: any) => regenerateStory(id!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['story', id] });
      setShowRegenForm(false);
    },
  });

  const matMut = useMutation({
    mutationFn: () => materializeStory(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['story', id] });
      navigate(`/projects/${id}/timeline`);
    },
  });

  const handleGenerate = () => {
    if (concept.trim().length < 10) {
      alert('Story concept must be at least 10 characters long.');
      return;
    }
    genMut.mutate({
      concept,
      style: project?.style || '2d_chinese_donghua',
      target_episodes: 1,
      episode_duration_minutes: 1.5,
      language: 'vietnamese',
    });
  };

  const handleRegenerate = () => {
    if (concept.trim().length < 10) {
      alert('Story concept must be at least 10 characters long.');
      return;
    }
    regenMut.mutate({
      concept,
      style: project?.style || '2d_chinese_donghua',
      target_episodes: 1,
      episode_duration_minutes: 1.5,
      language: 'vietnamese',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-500/30 border-t-accent-500 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading story bible...</p>
        </div>
      </div>
    );
  }

  const noStory = isError || !bible;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Story Lab</h1>
          <p className="text-sm text-gray-500 mt-1">Story bible & episode editor</p>
        </div>
        <div className="flex gap-2">
          {!noStory && (
            <>
              <button
                onClick={() => setShowRegenForm(!showRegenForm)}
                className="btn-secondary flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                </svg>
                Regenerate
              </button>
              <button
                onClick={() => matMut.mutate()}
                disabled={matMut.isPending}
                className="btn-primary flex items-center gap-2"
              >
                {matMut.isPending ? (
                  <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Materializing...</>
                ) : (
                  <><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg> Materialize</>
                )}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Regeneration form card */}
      {showRegenForm && (
        <div className="card p-5 border-amber-500/25 animate-slide-up space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-white">Regenerate Story Bible</h3>
            <p className="text-[10px] text-gray-500 mt-0.5">Modify the concept to regenerate character sheets, outline, and scenes</p>
          </div>
          <textarea
            value={concept}
            onChange={(e) => setConcept(e.target.value)}
            rows={4}
            className="input-field resize-none leading-relaxed text-xs"
            placeholder="Edit your story concept (min 10 chars)..."
          />
          <div className="flex gap-2">
            <button
              onClick={handleRegenerate}
              disabled={concept.trim().length < 10 || regenMut.isPending}
              className="btn-primary py-1 px-3 text-xs"
            >
              {regenMut.isPending ? 'Regenerating...' : 'Confirm Regenerate'}
            </button>
            <button
              onClick={() => setShowRegenForm(false)}
              className="btn-secondary py-1 px-3 text-xs"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {noStory ? (
        <div className="card-glow max-w-2xl mx-auto my-10 animate-slide-up">
          <div className="card p-6 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-500/20 flex items-center justify-center text-lg shadow-lg">
                📖
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Generate Story Bible</h2>
                <p className="text-xs text-gray-500 mt-0.5">Describe your concept to let AI generate outline and characters</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 block mb-1.5 font-medium">Story Concept / Ý tưởng kịch bản (Vietnamese or English)</label>
                <textarea
                  value={concept}
                  onChange={(e) => setConcept(e.target.value)}
                  rows={6}
                  className="input-field resize-none leading-relaxed text-sm font-light"
                  placeholder="Nhập ý tưởng kịch bản của bạn (tối thiểu 10 ký tự)... Ví dụ: Lâm Hàn là một đệ tử ngoại môn của Hoa Sơn Phái. Trong một lần rơi xuống vực sâu, anh tình cờ nhặt được một thanh cổ kiếm chứa phong ấn của Kiếm Ma..."
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={concept.trim().length < 10 || genMut.isPending}
                className="btn-primary w-full flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 py-2.5"
              >
                {genMut.isPending ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Generating Story Bible (may take 1-2 minutes)...
                  </>
                ) : (
                  <>
                    <span>✨</span>
                    Generate Story Bible
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Series Overview */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center text-white text-lg shadow-lg shadow-blue-500/20">
                📖
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">{bible.series_name}</h2>
                <div className="flex gap-2 mt-1">
                  <span className="badge bg-blue-500/10 text-blue-400 border border-blue-500/20">{bible.target_audience}</span>
                  <span className="badge bg-violet-500/10 text-violet-400 border border-violet-500/20">{bible.total_episodes} episodes</span>
                  <span className="badge bg-amber-500/10 text-amber-400 border border-amber-500/20">{bible.episode_duration_minutes}m each</span>
                </div>
              </div>
            </div>
            <p className="text-sm text-gray-300 leading-relaxed">{bible.series_overview}</p>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {bible.genre?.map((g: string) => (
                <span key={g} className="badge bg-accent-500/10 text-accent-300 border border-accent-500/15">{g}</span>
              ))}
            </div>
            {bible.themes && bible.themes.length > 0 && (
              <div className="mt-3 pt-3 border-t border-accent-500/10">
                <span className="text-xs text-gray-500 font-medium">Themes: </span>
                <span className="text-xs text-gray-400">{bible.themes.join(', ')}</span>
              </div>
            )}
            {bible.key_locations && bible.key_locations.length > 0 && (
              <div className="mt-2">
                <span className="text-xs text-gray-500 font-medium">Locations: </span>
                <span className="text-xs text-gray-400">{bible.key_locations.join(', ')}</span>
              </div>
            )}
          </div>

          {/* Characters */}
          {bible.characters && bible.characters.length > 0 && (
            <div>
              <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                <span>👤</span> Characters
                <span className="text-sm font-normal text-gray-500">({bible.characters.length})</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {bible.characters.map((c: any) => (
                  <div key={c.name} className="card p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/20 flex items-center justify-center text-lg shrink-0">
                        👤
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-semibold text-white text-sm">{c.name}</h3>
                        <span className="badge bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">{c.role}</span>
                        <p className="text-xs text-gray-400 mt-1.5">{c.personality}</p>
                      </div>
                    </div>
                    {c.backstory && (
                      <p className="text-xs text-gray-500 mt-2 pt-2 border-t border-accent-500/10">{c.backstory}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Episodes */}
          {bible.episodes && bible.episodes.length > 0 && (
            <div>
              <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                <span>🎬</span> Episodes
                <span className="text-sm font-normal text-gray-500">({bible.episodes.length})</span>
              </h2>
              <div className="space-y-3">
                {bible.episodes.map((ep: any) => (
                  <div key={ep.number} className="card p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/20 border border-violet-500/20 flex items-center justify-center text-sm font-bold text-violet-400 shrink-0">
                        {String(ep.number).padStart(2, '0')}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="font-semibold text-white text-sm">{ep.title}</h3>
                        <p className="text-xs text-gray-400 mt-1 leading-relaxed">{ep.summary}</p>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-[10px] text-gray-500">
                            🎬 {ep.scenes?.length || 0} scenes
                          </span>
                          {ep.scenes && ep.scenes.length > 0 && (
                            <span className="text-[10px] text-gray-500">
                              ⏱️ {ep.scenes.reduce((acc: number, s: any) => acc + (s.duration_seconds || 0), 0)}s total
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Continuity Notes */}
          {bible.continuity_notes && (
            <div className="card p-4 border-amber-500/10">
              <div className="flex items-start gap-3">
                <span className="text-lg">📋</span>
                <div>
                  <h3 className="text-sm font-semibold text-amber-400">Continuity Notes</h3>
                  <p className="text-xs text-gray-400 mt-1">{bible.continuity_notes}</p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
