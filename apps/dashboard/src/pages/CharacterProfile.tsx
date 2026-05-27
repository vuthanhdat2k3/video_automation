import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getCharacters,
  updateCharacter,
  generateCharacterSheet,
  generateOutfitSheet,
  generateAssetSheet,
  generateExpressionSheet,
  generateFullReference,
  getAssetDownloadUrl,
} from '../api/endpoints';
import { useState, useEffect } from 'react';

type TabId = 'views' | 'expressions' | 'outfits' | 'props';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'views', label: 'Views', icon: '📋' },
  { id: 'expressions', label: 'Expressions', icon: '😀' },
  { id: 'outfits', label: 'Outfits', icon: '👕' },
  { id: 'props', label: 'Props', icon: '⚔️' },
];

const VIEW_LABELS: Record<string, string> = {
  front: 'Front',
  back: 'Back',
  side: 'Side',
  three_quarter: '3/4',
};

const VIEW_ICONS: Record<string, string> = {
  front: '🧑',
  back: '🔙',
  side: '↔️',
  three_quarter: '🔄',
};

const EXPRESSION_LABELS: Record<string, string> = {
  neutral: 'Neutral',
  angry: 'Angry',
  smile: 'Smile',
  battle: 'Battle',
};

export default function CharacterProfile() {
  const { id, cid } = useParams<{ id: string; cid: string }>();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabId>('views');
  const [generating, setGenerating] = useState<TabId | null>(null);

  const { data: chars } = useQuery({
    queryKey: ['characters', id],
    queryFn: () => getCharacters(id!),
    enabled: !!id,
  });

  const character = chars?.find((c: any) => c.id === cid);
  const viewAssets: Record<string, string> = character?.character_json?.view_assets || {};
  const expressionAssets: Record<string, string> = character?.character_json?.expression_assets || {};
  const outfitAssets: Record<string, string> = character?.character_json?.outfit_assets || {};
  const propAssets: Record<string, string> = character?.character_json?.prop_assets || {};

  const hasAnyViews = ['front', 'back', 'side', 'three_quarter'].some((v) => viewAssets[v]);
  const hasExpressions = ['neutral', 'angry', 'smile', 'battle'].some((e) => expressionAssets[e]);

  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (character) {
      setName(character.name || '');
      setRole(character.role || '');
      setDescription(character.description || '');
    }
  }, [character]);

  const updateMut = useMutation({
    mutationFn: (data: any) => updateCharacter(cid!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['characters', id] });
    },
  });

  const genSheetMut = useMutation({
    mutationFn: () => generateCharacterSheet(cid!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['characters', id] }),
  });

  const genOutfitMut = useMutation({
    mutationFn: () => generateOutfitSheet(cid!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['characters', id] }),
  });

  const genAssetMut = useMutation({
    mutationFn: () => generateAssetSheet(cid!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['characters', id] }),
  });

  const genExpressionMut = useMutation({
    mutationFn: () => generateExpressionSheet(cid!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['characters', id] }),
  });

  const genFullMut = useMutation({
    mutationFn: () => generateFullReference(cid!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['characters', id] }),
  });

  const handleGenerate = async (tab: TabId) => {
    setGenerating(tab);
    try {
      if (tab === 'views') await genSheetMut.mutateAsync();
      else if (tab === 'outfits') await genOutfitMut.mutateAsync();
      else if (tab === 'props') await genAssetMut.mutateAsync();
      else if (tab === 'expressions') await genExpressionMut.mutateAsync();
    } catch (err) {
      console.error(err);
      alert(`Failed to generate ${tab}.`);
    } finally {
      setGenerating(null);
    }
  };

  if (!character) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-500/30 border-t-accent-500 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading character...</p>
        </div>
      </div>
    );
  }

  const hasChanges = name !== character.name || role !== character.role || description !== character.description;

  const renderViewGrid = (assets: Record<string, string>, keys: string[], labels: Record<string, string>, icons: Record<string, string>) => (
    <div className="grid grid-cols-2 gap-3">
      {keys.map((key) => {
        const assetId = assets[key];
        return (
          <div key={key} className="relative group">
            <div className="aspect-[9/16] rounded-xl bg-surface-800 border border-accent-500/10 overflow-hidden flex items-center justify-center">
              {assetId ? (
                <img
                  src={getAssetDownloadUrl(assetId)}
                  alt={key}
                  className="w-full h-full object-cover transition-all duration-300 group-hover:scale-105"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-gray-600">
                  <span className="text-2xl">{icons[key]}</span>
                  <span className="text-[9px] text-gray-600 text-center px-2">{labels[key]}</span>
                </div>
              )}
            </div>
            <div className={`absolute bottom-2 left-2 right-2 flex justify-center`}>
              {assetId ? (
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-black/60 backdrop-blur text-gray-300 block text-center truncate">
                  {labels[key]}
                </span>
              ) : (
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  Missing
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );

  const renderTabContent = () => {
    if (activeTab === 'views') {
      return (
        <div className="space-y-3">
          {renderViewGrid(viewAssets, ['front', 'back', 'side', 'three_quarter'], VIEW_LABELS, VIEW_ICONS)}
          {viewAssets.preview && (
            <div>
              <p className="text-[10px] text-gray-500 mb-1.5">Sheet Preview</p>
              <img
                src={getAssetDownloadUrl(viewAssets.preview)}
                alt="Sheet preview"
                className="w-full rounded-xl border border-accent-500/10"
              />
            </div>
          )}
        </div>
      );
    }
    if (activeTab === 'expressions') {
      return (
        <div className="space-y-3">
          {hasAnyViews ? (
            renderViewGrid(expressionAssets, ['neutral', 'angry', 'smile', 'battle'], EXPRESSION_LABELS, {
              neutral: '😐',
              angry: '😠',
              smile: '😊',
              battle: '⚡',
            })
          ) : (
            <div className="p-8 text-center text-gray-500 text-xs">
              Generate views first to enable expression generation.
            </div>
          )}
          {expressionAssets.preview && (
            <div>
              <p className="text-[10px] text-gray-500 mb-1.5">Expressions Preview</p>
              <img
                src={getAssetDownloadUrl(expressionAssets.preview)}
                alt="Expressions preview"
                className="w-full rounded-xl border border-accent-500/10"
              />
            </div>
          )}
        </div>
      );
    }
    if (activeTab === 'outfits') {
      const outfitKeys = Object.keys(outfitAssets).filter((k) => k !== 'preview');
      const outfitLabels: Record<string, string> = {};
      outfitKeys.forEach((k) => { outfitLabels[k] = k.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()); });
      const outfitIcons: Record<string, string> = {};
      outfitKeys.forEach((k) => { outfitIcons[k] = '👕'; });
      return (
        <div className="space-y-3">
          {outfitKeys.length > 0 ? (
            renderViewGrid(outfitAssets, outfitKeys, outfitLabels, outfitIcons)
          ) : (
            <div className="p-8 text-center text-gray-500 text-xs">
              No outfit items extracted. Update description with clothing details and regenerate.
            </div>
          )}
          {outfitAssets.preview && (
            <div>
              <p className="text-[10px] text-gray-500 mb-1.5">Outfits Preview</p>
              <img
                src={getAssetDownloadUrl(outfitAssets.preview)}
                alt="Outfits preview"
                className="w-full rounded-xl border border-accent-500/10"
              />
            </div>
          )}
        </div>
      );
    }
    if (activeTab === 'props') {
      const propKeys = Object.keys(propAssets).filter((k) => k !== 'preview');
      const propLabels: Record<string, string> = {};
      propKeys.forEach((k) => { propLabels[k] = k.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()); });
      const propIcons: Record<string, string> = {};
      propKeys.forEach((k) => { propIcons[k] = '⚔️'; });
      return (
        <div className="space-y-3">
          {propKeys.length > 0 ? (
            renderViewGrid(propAssets, propKeys, propLabels, propIcons)
          ) : (
            <div className="p-8 text-center text-gray-500 text-xs">
              No prop items extracted. Update description with equipment and regenerate.
            </div>
          )}
          {propAssets.preview && (
            <div>
              <p className="text-[10px] text-gray-500 mb-1.5">Props Preview</p>
              <img
                src={getAssetDownloadUrl(propAssets.preview)}
                alt="Props preview"
                className="w-full rounded-xl border border-accent-500/10"
              />
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  const isGenerating = generating !== null;

  return (
    <div className="animate-fade-in max-w-5xl space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link to={`/projects/${id}/characters`} className="text-gray-500 hover:text-white transition-colors">
          Characters
        </Link>
        <svg className="w-3.5 h-3.5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        <span className="text-white">{character.name || 'Edit Character'}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Tabbed Reference Panel (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          {/* Tabs */}
          <div className="card p-1.5">
            <div className="flex gap-1">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  disabled={isGenerating}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    activeTab === tab.id
                      ? 'bg-accent-500/15 text-accent-300 border border-accent-500/20'
                      : 'text-gray-500 hover:text-gray-300 border border-transparent'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Generate button per tab */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">
                {TABS.find((t) => t.id === activeTab)?.label}
              </h3>
              <p className="text-[10px] text-gray-500">
                {activeTab === 'views' && 'HiRes front + IPAdapter multi-view + face restore'}
                {activeTab === 'expressions' && '4 expressions with face restore (needs front view)'}
                {activeTab === 'outfits' && 'Extracted outfit items on white bg'}
                {activeTab === 'props' && 'Extracted props/weapons on white bg'}
              </p>
            </div>
            <button
              onClick={() => handleGenerate(activeTab)}
              disabled={isGenerating || updateMut.isPending}
              className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5"
            >
              {generating === activeTab ? (
                <><span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Generating...</>
              ) : (
                <><span className="text-sm">🎨</span> Generate</>
              )}
            </button>
          </div>

          {/* Tab content panel */}
          <div className="card p-5">
            {renderTabContent()}
          </div>

          {/* Full reference button */}
          <button
            onClick={() => genFullMut.mutateAsync()}
            disabled={isGenerating}
            className="w-full btn-secondary text-xs py-2 flex items-center justify-center gap-2"
          >
            {genFullMut.isPending ? (
              <><span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Generating Full Reference...</>
            ) : (
              <><span className="text-sm">🚀</span> Generate Full Reference (Views + Outfits + Props + Expressions)</>
            )}
          </button>

          {/* Progress overlay */}
          {generating && (
            <div className="p-3 rounded-lg bg-accent-500/5 border border-accent-500/20 flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-accent-500/30 border-t-accent-500 rounded-full animate-spin shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-accent-300 font-medium">
                  Generating {TABS.find((t) => t.id === generating)?.label}...
                </p>
                <p className="text-[10px] text-gray-500">
                  {generating === 'views' && 'HiRes front → IPAdapter views → face restore → stitch (est. ~4 min)'}
                  {generating === 'expressions' && '4 expressions × IPAdapter + face restore (est. ~3 min)'}
                  {generating === 'outfits' && 'Outfit items on white background (est. ~2 min)'}
                  {generating === 'props' && 'Prop items on white background (est. ~2 min)'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right: Character Details (2 cols) */}
        <div className="lg:col-span-2 card p-6 space-y-6">
          <div>
            <h2 className="text-lg font-bold text-white">Character Details</h2>
            <p className="text-xs text-gray-500 mt-0.5">Customize basic identity & look</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1.5 font-medium">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field"
                placeholder="Character name"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1.5 font-medium">Role</label>
              <div className="flex flex-wrap gap-2">
                {['protagonist', 'deuteragonist', 'antagonist', 'supporting', 'minor'].map((r) => (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all capitalize ${
                      role === r
                        ? 'bg-accent-500/20 text-accent-300 border border-accent-500/30'
                        : 'bg-surface-700 text-gray-400 border border-transparent hover:text-white'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1.5 font-medium">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={5}
                className="input-field resize-none leading-relaxed text-sm"
                placeholder="Describe character look and personality..."
              />
            </div>

            <div className="flex gap-2 pt-2">
              <button
                onClick={() => updateMut.mutate({ name, role, description })}
                disabled={updateMut.isPending || !hasChanges}
                className="btn-primary"
              >
                {updateMut.isPending ? 'Saving...' : 'Save Changes'}
              </button>
              <Link to={`/projects/${id}/characters`} className="btn-secondary">
                Back
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Generation Prompt */}
      {character.prompt && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">🤖</span>
            <h3 className="text-sm font-semibold text-white">English Prompt compiled by LLM</h3>
          </div>
          <pre className="text-xs text-gray-400 whitespace-pre-wrap leading-relaxed font-mono bg-deep-800 rounded-lg p-3 border border-accent-500/10">
            {character.prompt}
          </pre>
        </div>
      )}
    </div>
  );
}
