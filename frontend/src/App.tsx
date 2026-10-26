import { FormEvent, MouseEvent, ReactNode, useCallback, useEffect, useRef, useState } from 'react'


const API = import.meta.env.VITE_API_URL ?? 'https://collabverse-live-3.onrender.com/api/v1'

type User = { id: string; email: string; role: string; avatar_url?: string | null; profile?: { full_name?: string; headline?: string; company_name?: string; institution_name?: string; [key: string]: unknown } }
type Post = { id: string; author_id: string; post_type: string; content: string | null; created_at: string; like_count: number; comment_count: number; liked_by_me: boolean; media?: { id: string; media_type: string; media_url: string; thumbnail_url?: string | null }[] }
type PublicUser = { id: string; full_name: string; role: string; headline?: string | null; avatar_url?: string | null }
type Connection = { id: string; requester_id: string; recipient_id: string; status: string; created_at: string }
type PostComment = { id: string; post_id: string; user_id: string; content: string; created_at: string }

async function request<T>(path: string, token?: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    })
  } catch {
    throw new Error(`Can't reach the backend at ${API}. Check that the API server is running, then try again.`)
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    const detail = data?.detail
    throw new Error(Array.isArray(detail) ? detail.map((item: { msg: string }) => item.msg).join(', ') : detail || 'Something went wrong. Please try again.')
  }
  return response.status === 204 ? undefined as T : response.json()
}

async function uploadPostMedia(file: File, token: string): Promise<{ media_url: string; media_type: 'image' | 'video' }> {
  const body = new FormData()
  body.append('file', file)
  let response: Response
  try {
    response = await fetch(`${API}/posts/media/upload`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body })
  } catch {
    throw new Error('Could not reach the media upload service. Check that the backend is running.')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new Error(data?.detail || 'Could not upload this attachment.')
  }
  return response.json()
}

const roleName = (role?: string) => role?.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || 'Member'
const initials = (name: string) => name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase()
const timeAgo = (date: string) => {
  const mins = Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 60000))
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  if (mins < 1440) return `${Math.floor(mins / 60)}h ago`
  return `${Math.floor(mins / 1440)}d ago`
}
const isTestAccount = (member: PublicUser) => /(?:^|[\s._-])(?:test|demo|dummy|sample)(?:$|[\s._-])|bot/i.test(member.full_name)

function BrandLogo({ href = '#home', onClick }: { href?: string; onClick?: () => void }) {
  return <a className="brand" href={href} onClick={onClick} aria-label="CollabVerse home">
    <svg className="brand-symbol" viewBox="0 0 40 40" role="img" aria-hidden="true">
      <rect width="40" height="40" rx="12" fill="#3559d5" />
      <path d="M11.5 18.2c.9-4.4 4.4-7.3 8.7-7.3 3.1 0 5.6 1.3 7.2 3.6" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M28.5 21.8c-.9 4.4-4.4 7.3-8.7 7.3-3.1 0-5.6-1.3-7.2-3.6" fill="none" stroke="#bfe8ff" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="11.5" cy="18.2" r="2.2" fill="#fff" />
      <circle cx="28.5" cy="21.8" r="2.2" fill="#bfe8ff" />
      <circle cx="20" cy="20" r="3.2" fill="#fff" />
      <circle cx="20" cy="20" r="1.25" fill="#3559d5" />
    </svg>
    <span className="brand-wordmark"><strong>Collab</strong><span>Verse</span></span>
  </a>
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('cv_access_token') || '')
  const [onboardingPending, setOnboardingPending] = useState(() => localStorage.getItem('cv_onboarding_pending') === 'true')
  const [user, setUser] = useState<User | null>(null)
  const [posts, setPosts] = useState<Post[]>([])
  const [members, setMembers] = useState<PublicUser[]>([])
  const [savedPostIds, setSavedPostIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [authMode, setAuthMode] = useState<'login' | 'register'>(() => window.location.pathname === '/register' ? 'register' : 'login')
  const [googleSignupCode, setGoogleSignupCode] = useState('')
  const [activeNav, setActiveNavState] = useState('Home')
  const [projectsInitialTab, setProjectsInitialTab] = useState<'discover' | 'created'>('discover')
  const [viewingProfileId, setViewingProfileId] = useState('')
  const [messageMemberId, setMessageMemberId] = useState('')
  const [profileReturnNav, setProfileReturnNav] = useState('Home')
  const [draft, setDraft] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [attachments, setAttachments] = useState<File[]>([])
  const [attachmentPreviews, setAttachmentPreviews] = useState<{ file: File; url: string; mediaType: 'image' | 'video' }[]>([])
  const [attachmentError, setAttachmentError] = useState('')
  const [uploadProgress, setUploadProgress] = useState('')

  function setActiveNav(destination: string) {
    setViewingProfileId('')
    setActiveNavState(destination)
  }

  useEffect(() => {
    const previews = attachments.map((file) => ({ file, url: URL.createObjectURL(file), mediaType: file.type.startsWith('video/') ? 'video' as const : 'image' as const }))
    setAttachmentPreviews(previews)
    return () => previews.forEach((preview) => URL.revokeObjectURL(preview.url))
  }, [attachments])

  useEffect(() => {
    if (activeNav !== 'Projects') setProjectsInitialTab('discover')
  }, [activeNav])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const google = params.get('google')
    const code = params.get('code')
    if (!google) return
    window.history.replaceState({}, '', window.location.pathname)
    if (google === 'account_exists') {
      setError('This email already has a CollabVerse account. Continue with the Google account that was originally linked.')
      return
    }
    if (google === 'signup' && code) {
      setAuthMode('register')
      setGoogleSignupCode(code)
      setError('Finish setting up your profile and accept the Terms of Service to create your account.')
      return
    }
    if (google === 'login' && code) {
      void request<{ access_token: string }>('/auth/google/exchange', undefined, { method: 'POST', body: JSON.stringify({ code }) })
        .then((result) => { localStorage.setItem('cv_access_token', result.access_token); setToken(result.access_token) })
        .catch((reason) => setError(reason instanceof Error ? reason.message : 'Google sign-in could not be completed.'))
    }
  }, [])

  const loadApp = useCallback(async (accessToken: string) => {
    setLoading(true); setError('')
    try {
      const current = await request<User>('/users/me', accessToken)
      const home = onboardingPending ? { feed: [] as Post[] } : await request<{ feed: Post[] }>('/home', accessToken)
      let directory: PublicUser[] = []
      let mediaPosts: Post[] = []
      let savedIds: string[] = []
      if (!onboardingPending) {
        [directory, mediaPosts, savedIds] = await Promise.all([
          request<PublicUser[]>('/users/directory?limit=100', accessToken).catch(() => [] as PublicUser[]),
          request<Post[]>('/posts/feed?limit=20&offset=0', accessToken).catch(() => [] as Post[]),
          request<string[]>('/posts/saved/ids', accessToken).catch(() => [] as string[]),
        ])
      }
      let profile: User['profile']
      try { profile = (await request<{ profile: User['profile'] }>('/profiles/me', accessToken)).profile } catch { /* profile is optional for the shell */ }
      const mediaByPost = new Map(mediaPosts.map((post) => [post.id, post.media || []]))
      const visibleDirectory = directory.filter((member) => !isTestAccount(member))
      const visibleIds = new Set(visibleDirectory.map((member) => member.id))
      const testAccountIds = new Set(directory.filter(isTestAccount).map((member) => member.id))
      setUser({ ...current, profile }); setMembers(visibleDirectory); setSavedPostIds(savedIds); setPosts((home.feed || []).filter((post) => !testAccountIds.has(post.author_id)).map((post) => ({ ...post, media: mediaByPost.get(post.id) || [] })))
      if (window.location.pathname === '/login' || window.location.pathname === '/register') {
        window.history.replaceState({}, '', '/')
      }
    } catch (reason) {
      if (localStorage.getItem('cv_access_token') !== accessToken) return
      localStorage.removeItem('cv_access_token'); setToken(''); setUser(null)
      setError(reason instanceof Error ? reason.message : 'Could not load your feed.')
    } finally { setLoading(false) }
  }, [onboardingPending])

  useEffect(() => { if (token) void loadApp(token) }, [token, loadApp])

  function openPublicProfile(memberId: string) {
    if (user && memberId === user.id) { setActiveNav('My profile'); setViewingProfileId(''); return }
    setProfileReturnNav(activeNav)
    setViewingProfileId(memberId)
  }

  function messageMember(memberId: string) {
    setViewingProfileId('')
    setMessageMemberId(memberId)
    setActiveNav('Messages')
  }

  function closePublicProfile() {
    setViewingProfileId('')
    setActiveNav(profileReturnNav)
  }

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('')
    const form = new FormData(event.currentTarget)
    try {
      const result = authMode === 'login'
        ? await request<{ access_token: string }>('/auth/login', undefined, { method: 'POST', body: JSON.stringify({ email: String(form.get('email') || ''), password: String(form.get('password') || '') }) })
        : googleSignupCode
          ? await request<{ access_token: string }>('/auth/google/signup', undefined, { method: 'POST', body: JSON.stringify({ code: googleSignupCode, password: String(form.get('password') || ''), full_name: String(form.get('name') || ''), role: String(form.get('role') || 'student'), accepted_terms: form.get('accepted_terms') === 'on', website: String(form.get('website') || ''), company_name: String(form.get('organization') || '') || null, institution_name: String(form.get('organization') || '') || null }) })
          : null
      if (!result) { setError('Continue with Google to verify your email and create an account.'); return }
      if (authMode === 'register') {
        localStorage.setItem('cv_onboarding_pending', 'true')
        setOnboardingPending(true)
      } else {
        localStorage.removeItem('cv_onboarding_pending')
        setOnboardingPending(false)
      }
      localStorage.setItem('cv_access_token', result.access_token)
      setToken(result.access_token)
      setGoogleSignupCode('')
      setActiveNav('Home')
      window.history.replaceState({}, '', '/')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to sign in.') }
  }

  async function publish(event: FormEvent) {
    event.preventDefault(); if ((!draft.trim() && !attachments.length) || !token) return
    setPublishing(true); setError(''); setAttachmentError('')
    try {
      const uploaded = [] as { media_type: 'image' | 'video'; media_url: string; position: number }[]
      for (let index = 0; index < attachments.length; index += 1) {
        setUploadProgress(`Uploading ${index + 1} of ${attachments.length}…`)
        const media = await uploadPostMedia(attachments[index], token)
        uploaded.push({ ...media, position: index })
      }
      setUploadProgress(attachments.length ? 'Publishing your post…' : '')
      await request('/posts', token, { method: 'POST', body: JSON.stringify({ content: draft.trim() || null, post_type: uploaded.length ? 'media' : 'text', media: uploaded }) })
      const [home, mediaPosts] = await Promise.all([
        request<{ feed: Post[] }>('/home', token),
        request<Post[]>('/posts/feed?limit=20&offset=0', token).catch(() => [] as Post[]),
      ])
      const mediaByPost = new Map(mediaPosts.map((post) => [post.id, post.media || []]))
      setDraft(''); setAttachments([]); setAttachmentPreviews([]); setPosts((home.feed || []).map((post) => ({ ...post, media: mediaByPost.get(post.id) || [] })))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not publish your post.') }
    finally { setPublishing(false); setUploadProgress('') }
  }

  function addAttachments(files: FileList | null) {
    if (!files?.length) return
    setAttachmentError('')
    const allowed = ['image/jpeg', 'image/png', 'image/webp', 'video/mp4', 'video/webm']
    const picked = Array.from(files)
    const invalid = picked.find((file) => !allowed.includes(file.type))
    if (invalid) { setAttachmentError('Choose JPG, PNG, WebP, MP4, or WebM files.'); return }
    const oversized = picked.find((file) => file.size > (file.type.startsWith('video/') ? 100 : 10) * 1024 * 1024)
    if (oversized) { setAttachmentError(oversized.type.startsWith('video/') ? 'Videos must be 100 MB or smaller.' : 'Images must be 10 MB or smaller.'); return }
    if (attachments.length + picked.length > 10) { setAttachmentError('A post can contain up to 10 attachments.'); return }
    setAttachments((current) => [...current, ...picked])
  }

  async function toggleLike(post: Post) {
    if (!token) return
    try {
      const result = await request<{ liked: boolean; like_count: number }>(`/posts/${post.id}/like`, token, { method: 'POST' })
      setPosts((current) => current.map((item) => item.id === post.id ? { ...item, liked_by_me: result.liked, like_count: result.like_count } : item))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update like.') }
  }

  async function toggleSavePost(postId: string): Promise<boolean> {
    const saved = savedPostIds.includes(postId)
    const result = await request<{ post_id: string; saved: boolean }>(`/posts/${postId}/save`, token, { method: saved ? 'DELETE' : 'PUT' })
    setSavedPostIds((current) => result.saved ? [...new Set([...current, postId])] : current.filter((id) => id !== postId))
    return result.saved
  }

  async function deletePost(post: Post): Promise<boolean> {
    if (!window.confirm('Delete this post? This cannot be undone.')) return false
    try {
      await request(`/posts/${post.id}`, token, { method: 'DELETE' })
      setPosts((current) => current.filter((item) => item.id !== post.id))
      setSavedPostIds((current) => current.filter((id) => id !== post.id))
      return true
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not delete this post.'); return false }
  }

  function signOut() { localStorage.removeItem('cv_access_token'); localStorage.removeItem('cv_onboarding_pending'); setToken(''); setOnboardingPending(false); setUser(null); setPosts([]); setMembers([]); setSavedPostIds([]); setViewingProfileId(''); setAuthMode('login'); window.history.replaceState({}, '', '/login') }

  if (token && !user) return <main className="session-restoring" aria-live="polite" aria-busy="true"><BrandLogo href="/" /><span className="loading-spinner" /><p>Restoring your CollabVerse session…</p></main>
  if (!token || !user) return <AuthScreen mode={authMode} setMode={(mode) => { setAuthMode(mode); window.history.replaceState({}, '', mode === 'login' ? '/login' : '/register'); if (mode === 'login') setGoogleSignupCode('') }} onSubmit={authenticate} error={error} googleSignupCode={googleSignupCode} />
  if (onboardingPending) return <OnboardingScreen token={token} user={user} onComplete={() => { localStorage.removeItem('cv_onboarding_pending'); setOnboardingPending(false); setActiveNav('Home') }} />

  const name = user.profile?.full_name || user.email.split('@')[0]
  const headline = user.profile?.headline || user.profile?.company_name || user.profile?.institution_name || `${roleName(user.role)} · CollabVerse`

  return <div className="app-shell">
    <header className="topbar">
      <BrandLogo onClick={() => setActiveNav('Home')} />
      <GlobalSearch token={token} members={members} posts={posts} onNavigate={setActiveNav} onOpenProfile={openPublicProfile} />
      <nav className="global-nav" aria-label="Main navigation">{[['My network','network'],['Opportunities','opportunities'],['Mentorship','mentorship'],['Messages','messages']].map(([label, icon]) => <button key={label} aria-label={label} title={label} className={`global-nav-item ${activeNav === label ? 'global-active' : ''}`} onClick={() => setActiveNav(label)}><Icon name={icon} size={18} /><span>{label}</span></button>)}</nav>
      <div className="top-actions"><NotificationMenu token={token} members={members} onNavigate={setActiveNav} /><button className="top-profile" onClick={() => setActiveNav('My profile')}><Avatar name={name} imageUrl={user.avatar_url} /><span>{name}</span><Icon name="chevron" size={14} /></button><button className="signout" onClick={signOut}>Sign out</button></div>
    </header>
    <div className="workspace">
      <aside className="left-rail">
        <section className="rail-profile-card card"><div className="rail-profile-cover" /><Avatar name={name} imageUrl={user.avatar_url} /><strong>{name}</strong><span>{headline}</span><div className="rail-profile-meta"><span>{roleName(user.role)}</span><span>•</span><span>CollabVerse member</span></div></section>
        <button className={`nav-item rail-home-item ${activeNav === 'Home' ? 'selected' : ''}`} onClick={() => setActiveNav('Home')}><span className="nav-icon"><Icon name="home" size={17} /></span>Home</button>
        <nav className="rail-responsive-links" aria-label="More workspace links"><div className="rail-label">EXPLORE</div><button className={`nav-item ${activeNav === 'News' ? 'selected' : ''}`} onClick={() => setActiveNav('News')}><span className="nav-icon"><Icon name="news" size={17} /></span>News</button><button className={`nav-item ${activeNav === 'AI mentor' ? 'selected' : ''}`} onClick={() => setActiveNav('AI mentor')}><span className="nav-icon"><Icon name="ai" size={17} /></span>AI mentor</button><button className={`nav-item ${activeNav === 'Courses' ? 'selected' : ''}`} onClick={() => setActiveNav('Courses')}><span className="nav-icon"><Icon name="courses" size={17} /></span>Courses</button>{user.role === 'student' && <button className={`nav-item ${activeNav === 'Daily assessment' ? 'selected' : ''}`} onClick={() => setActiveNav('Daily assessment')}><span className="nav-icon"><Icon name="assessment" size={17} /></span>Daily assessment</button>}<button className={`nav-item ${activeNav === 'Projects' ? 'selected' : ''}`} onClick={() => setActiveNav('Projects')}><span className="nav-icon"><Icon name="projects" size={17} /></span>Projects</button><button className={`nav-item ${activeNav === 'Hackathons' ? 'selected' : ''}`} onClick={() => setActiveNav('Hackathons')}><span className="nav-icon"><Icon name="assessment" size={17} /></span>Hackathons</button><button className={`nav-item ${activeNav === 'Mentorship' ? 'selected' : ''}`} onClick={() => setActiveNav('Mentorship')}><span className="nav-icon"><Icon name="mentorship" size={17} /></span>Mentorship</button></nav>
        <div className="rail-label rail-label-space">YOUR SPACE</div>
        <button className={`nav-item ${activeNav === 'My profile' ? 'selected' : ''}`} onClick={() => setActiveNav('My profile')}><span className="nav-icon"><Icon name="profile" size={17} /></span>My profile</button><button className={`nav-item ${activeNav === 'Saved posts' ? 'selected' : ''}`} onClick={() => setActiveNav('Saved posts')}><span className="nav-icon"><Icon name="bookmark" size={17} /></span>Saved posts{savedPostIds.length > 0 && <span className="nav-count">{savedPostIds.length}</span>}</button>
        <div className="upgrade-card"><div className="upgrade-icon">✳</div><strong>Make your next move</strong><p>Discover opportunities that match your goals.</p><button onClick={() => setActiveNav('Opportunities')}>Explore opportunities <span>↗</span></button></div>
        <div className="rail-footer"><span>About</span><span>Guidelines</span><span>Privacy</span><small>© 2026 CollabVerse</small></div>
      </aside>

      <main className="feed-column">
        <div key={`${activeNav}-${viewingProfileId || 'workspace'}`} className="page-transition"><div className="page-heading"><div><div className="eyebrow">YOUR PROFESSIONAL COMMUNITY</div><h1>{viewingProfileId ? 'Member profile' : activeNav === 'Home' ? 'Your feed' : activeNav}</h1><p>{viewingProfileId ? 'Background, interests, and professional work.' : ({ Home: 'Fresh public posts from across CollabVerse.', Explore: 'Everything you need to learn, connect, and collaborate.', 'My network': 'Build meaningful professional connections.', 'My profile': 'Shape how people discover and work with you.', News: 'Research, industry, and ideas picked for your interests.', Hackathons: 'Discover challenges, prizes, and build opportunities.', 'AI mentor': 'Get thoughtful help with learning, career, and project goals.', Courses: 'Find trusted courses that match the skills you want to build.', 'Daily assessment': 'Practice a little each day and track your progress.', Projects: 'Find collaborators and move good ideas forward.', Mentorship: 'Learn from people with experience in your field.', Messages: 'Continue conversations with your community.', 'Saved posts': 'Return to the ideas you saved.' } as Record<string, string>)[activeNav] || 'Explore your professional community.'}</p></div></div>
        {error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}
          {viewingProfileId ? <PublicProfileScreen token={token} user={user} memberId={viewingProfileId} members={members} onBack={closePublicProfile} onMessage={messageMember} /> : activeNav === 'Explore' ? <ExploreScreen onNavigate={setActiveNav} isStudent={user.role === 'student'} /> : activeNav === 'My network' ? <NetworkScreen token={token} currentUserId={user.id} setError={setError} onOpenProfile={openPublicProfile} onMessage={messageMember} /> : activeNav === 'My profile' ? <ProfileScreen token={token} user={user} setUser={setUser} setError={setError} onViewAllProjects={() => { setProjectsInitialTab('created'); setActiveNav('Projects') }} /> : activeNav === 'News' ? <NewsScreen token={token} /> : activeNav === 'Hackathons' ? <HackathonsScreen token={token} /> : activeNav === 'AI mentor' ? <AIMentorScreen token={token} /> : activeNav === 'Courses' ? <CoursesScreen token={token} onNavigate={setActiveNav} /> : activeNav === 'Daily assessment' ? <DailyAssessmentScreen token={token} user={user} onNavigate={setActiveNav} /> : activeNav === 'Messages' ? <MessagesScreen token={token} user={user} members={members} initialMemberId={messageMemberId} /> : activeNav === 'Projects' ? <ProjectsScreen token={token} user={user} members={members} initialTab={projectsInitialTab} /> : activeNav === 'Mentorship' ? <MentorshipScreen token={token} user={user} members={members} onMessage={messageMember} /> : activeNav === 'Opportunities' ? <OpportunitiesComingSoon onNavigate={setActiveNav} /> : activeNav === 'Saved posts' ? <SavedPostsScreen token={token} user={user} members={members} savedPostIds={savedPostIds} onToggleSave={toggleSavePost} onDeletePost={deletePost} onOpenProfile={openPublicProfile} /> : <>
          <form className="composer card" onSubmit={publish}><div className="composer-row"><Avatar name={name} imageUrl={user.avatar_url} /><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Share an idea, a milestone, or something you’re working on…" rows={2} maxLength={5000} /></div>{attachmentPreviews.length > 0 && <div className="composer-attachment-grid">{attachmentPreviews.map((attachment, index) => <div className="composer-attachment-preview" key={`${attachment.file.name}-${index}`}>{attachment.mediaType === 'image' ? <img src={attachment.url} alt={attachment.file.name} /> : <video src={attachment.url} controls /> }<span>{attachment.file.name}</span><button type="button" disabled={publishing} aria-label={`Remove ${attachment.file.name}`} onClick={() => setAttachments((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button></div>)}</div>}{attachmentError && <div className="composer-attachment-error">{attachmentError}</div>}<div className="composer-bottom"><div className="composer-attach-actions"><label className="composer-attach-button"><Icon name="image" size={16} /><span>Photo / video</span><input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" multiple disabled={publishing || attachments.length >= 10} onChange={(event) => { addAttachments(event.currentTarget.files); event.currentTarget.value = '' }} /></label><span className="composer-note">Thoughtful contributions build stronger communities.</span></div><div><span className="char-count">{uploadProgress || (draft.length > 0 ? `${draft.length}/5000` : '')}</span><button className="primary-button" disabled={(!draft.trim() && !attachments.length) || publishing}>{publishing ? 'Sharing…' : 'Share post'} <span>↗</span></button></div></div></form>
          <div className="feed-toolbar"><span>{loading ? 'Loading your network…' : `${posts.length} recent ${posts.length === 1 ? 'update' : 'updates'}`}</span><button>Most relevant <span className="chevron">⌄</span></button></div>
          <section className="post-list">{!loading && posts.length === 0 && <div className="empty-state card"><div className="empty-illustration">✳</div><h2>Your network starts here</h2><p>Share what you’re working on or connect with people across academia and industry to bring your feed to life.</p><button className="primary-button" onClick={() => document.querySelector('textarea')?.focus()}>Write your first post</button></div>}{posts.map((post) => <PostCard key={post.id} post={post} currentUser={user} token={token} members={members} onOpenProfile={openPublicProfile} saved={savedPostIds.includes(post.id)} onToggleSave={() => toggleSavePost(post.id)} onDelete={() => void deletePost(post)} onLike={() => void toggleLike(post)} onCommentPosted={() => setPosts((current) => current.map((item) => item.id === post.id ? { ...item, comment_count: item.comment_count + 1 } : item))} />)}</section>
        </>}</div>
      </main>

      <aside className="right-rail"><section className="profile-card card"><div className="profile-cover" /><div className="profile-summary"><Avatar name={name} large imageUrl={user.avatar_url} /><h2>{name}</h2><p>{headline}</p><span className="role-pill">{roleName(user.role)}</span></div><div className="profile-stats"><div><strong>—</strong><span>Connections</span></div><div><strong>—</strong><span>Profile views</span></div></div></section>{!viewingProfileId && activeNav === 'Home' && <TopNewsWidget token={token} onNavigate={setActiveNav} />}
        <section className="right-card card"><div className="right-card-heading"><h3>Worth exploring</h3><span className="spark">✳</span></div><a href="#network" onClick={() => setActiveNav('My network')} className="suggestion"><span className="suggestion-icon indigo">♧</span><span><strong>Grow your network</strong><small>Connect across disciplines</small></span><span className="arrow">→</span></a><a href="#opportunities" onClick={() => setActiveNav('Opportunities')} className="suggestion"><span className="suggestion-icon teal">▧</span><span><strong>Find opportunities</strong><small>Research, projects & roles</small></span><span className="arrow">→</span></a><a href="#mentorship" onClick={() => setActiveNav('Mentorship')} className="suggestion"><span className="suggestion-icon amber">◇</span><span><strong>Explore mentorship</strong><small>Learn from experienced people</small></span><span className="arrow">→</span></a><div className="right-card-footer">Curated for your professional journey</div></section>
        <div className="quote-card"><span>“</span><p>Great work happens when different perspectives meet.</p><small>THE COLLABVERSE COMMUNITY</small></div>
      </aside>
    </div>
    <nav className="mobile-nav" aria-label="Main navigation">{[['Home','home'],['My network','network'],['Explore','courses'],['Messages','messages'],['My profile','profile']].map(([label, icon]) => <button key={label} aria-label={label} className={activeNav === label || (label === 'Explore' && ['News','AI mentor','Courses','Daily assessment','Projects','Hackathons','Mentorship','Opportunities','Saved posts'].includes(activeNav)) ? 'mobile-selected' : ''} onClick={() => setActiveNav(label)}><Icon name={icon} size={17} /><span>{label}</span></button>)}</nav>
  </div>
}

export default App

type NotificationItem = { id: string; actor_id?: string | null; notification_type: string; title: string; message?: string | null; entity_type?: string | null; entity_id?: string | null; is_read: boolean; created_at: string }

function NotificationMenu({ token, members, onNavigate }: { token: string; members: PublicUser[]; onNavigate: (destination: string) => void }) {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState<'all' | 'unread'>('all')

  async function refresh(showLoading = false) {
    if (showLoading) setLoading(true)
    try {
      const [list, count] = await Promise.all([
        request<{ notifications: NotificationItem[] }>('/notifications?limit=30&offset=0', token),
        request<{ unread_count: number }>('/notifications/unread-count', token),
      ])
      setItems(list.notifications || []); setUnread(count.unread_count || 0); setError('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load notifications.') }
    finally { if (showLoading) setLoading(false) }
  }
  useEffect(() => { void refresh(); const timer = window.setInterval(() => { void refresh() }, 20000); return () => window.clearInterval(timer) }, [token])

  async function markRead(item: NotificationItem) {
    if (item.is_read) return
    try {
      await request(`/notifications/${item.id}/read`, token, { method: 'PATCH' })
      setItems((current) => current.map((notification) => notification.id === item.id ? { ...notification, is_read: true } : notification))
      setUnread((current) => Math.max(0, current - 1))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update this notification.') }
  }
  async function markAllRead() {
    if (!unread) return
    try {
      await request('/notifications/read-all', token, { method: 'PATCH' })
      setItems((current) => current.map((item) => ({ ...item, is_read: true }))); setUnread(0)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not mark notifications as read.') }
  }
  async function remove(item: NotificationItem, event: MouseEvent) {
    event.stopPropagation()
    try {
      await request(`/notifications/${item.id}`, token, { method: 'DELETE' })
      setItems((current) => current.filter((notification) => notification.id !== item.id))
      if (!item.is_read) setUnread((current) => Math.max(0, current - 1))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not remove this notification.') }
  }
  function openNotification(item: NotificationItem) {
    void markRead(item)
    const type = item.notification_type
    if (type.startsWith('mentor_') || item.entity_type === 'mentorship') onNavigate('Mentorship')
    else if (type.startsWith('project_') || type === 'application_update' || item.entity_type === 'project') onNavigate('Projects')
    else if (type.startsWith('connection_') || item.entity_type === 'connection') onNavigate('My network')
    else onNavigate('Home')
    setOpen(false)
  }
  const shown = items.filter((item) => filter === 'all' || !item.is_read)

  return <div className="notification-menu-wrap"><button className="icon-button notification-button" title="Notifications" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`} aria-expanded={open} onClick={() => { setOpen((value) => !value); if (!open) void refresh(true) }}><Icon name="bell" size={19} />{unread > 0 && <i className="notification-count-badge">{unread > 99 ? '99+' : unread}</i>}</button>{open && <><button className="notification-dismiss" aria-label="Close notifications" onClick={() => setOpen(false)} /><section className="notification-popover card" aria-label="Notifications"><header className="notification-popover-header"><div><span className="eyebrow">YOUR ACTIVITY</span><h2>Notifications{unread > 0 && <span>{unread}</span>}</h2></div><button onClick={() => void markAllRead()} disabled={!unread}>Mark all read</button></header><div className="notification-filters"><button className={filter === 'all' ? 'notification-filter-active' : ''} onClick={() => setFilter('all')}>All</button><button className={filter === 'unread' ? 'notification-filter-active' : ''} onClick={() => setFilter('unread')}>Unread{unread > 0 && <span>{unread}</span>}</button></div>{error && <div className="notification-error">{error}</div>}<div className="notification-list">{loading ? <div className="notification-empty"><span className="loading-spinner" /><p>Loading notifications…</p></div> : shown.length ? shown.map((item) => { const actor = item.actor_id ? members.find((member) => member.id === item.actor_id) : undefined; return <article key={item.id} role="button" tabIndex={0} className={`notification-item ${item.is_read ? '' : 'notification-unread'}`} onClick={() => openNotification(item)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') openNotification(item) }}><span className={`notification-kind notification-kind-${item.notification_type.split('_')[0]}`}><Icon name={item.notification_type.startsWith('mentor_') ? 'mentorship' : item.notification_type.startsWith('connection_') ? 'network' : item.notification_type.startsWith('project_') || item.notification_type === 'application_update' ? 'projects' : 'bell'} size={16} /></span><span className="notification-content"><strong>{item.title}</strong>{item.message && <small>{item.message}</small>}<span className="notification-meta">{actor ? `From ${actor.full_name} · ` : ''}{timeAgo(item.created_at)}</span></span>{!item.is_read && <i className="notification-unread-dot" />}<button className="notification-remove" aria-label="Remove notification" title="Remove" onClick={(event) => void remove(item, event)}>×</button></article>}) : <div className="notification-empty"><span className="message-empty-icon"><Icon name="bell" size={20} /></span><strong>{filter === 'unread' ? 'You’re all caught up' : 'No notifications yet'}</strong><p>{filter === 'unread' ? 'New activity will show here.' : 'Updates about your network and collaborations will show here.'}</p></div>}</div><footer className="notification-popover-footer">Recent activity from your CollabVerse community</footer></section></>}</div>
}

type SearchProject = { id: string; title: string; description: string; domain?: string | null; project_type: string; difficulty: string }
type SearchMentor = { id: string; user_id: string; headline?: string | null; designation?: string | null; mentor_domains: string[]; mentoring_topics: string[]; mentoring_mode: string }
type SearchResult = { key: string; kind: 'Person' | 'Project' | 'Mentor' | 'Post'; title: string; detail: string; icon: string; destination: string; memberId?: string }

function GlobalSearch({ token, members, posts, onNavigate, onOpenProfile }: { token: string; members: PublicUser[]; posts: Post[]; onNavigate: (destination: string) => void; onOpenProfile: (memberId: string) => void }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [remoteProjects, setRemoteProjects] = useState<SearchProject[]>([])
  const [remoteMentors, setRemoteMentors] = useState<SearchMentor[]>([])
  const [remotePosts, setRemotePosts] = useState<Post[]>([])
  const [hasLoadedSearchData, setHasLoadedSearchData] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setOpen(true); requestAnimationFrame(() => inputRef.current?.focus()) }
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
  useEffect(() => {
    const term = query.trim()
    if (term.length < 2 || hasLoadedSearchData) { setLoading(false); return }
    let current = true
    setLoading(true)
    const timer = window.setTimeout(() => {
      Promise.all([
        request<SearchProject[]>('/projects?limit=100&skip=0&status=open', token).catch(() => []),
        request<SearchMentor[]>('/mentorship/mentors/discover?limit=100&offset=0&accepting_only=true', token).catch(() => []),
        request<Post[]>('/posts/feed?limit=50&offset=0', token).catch(() => []),
      ]).then(([projectData, mentorData, postData]) => {
        if (!current) return
        setRemoteProjects(projectData); setRemoteMentors(mentorData); setRemotePosts(postData); setHasLoadedSearchData(true)
      }).finally(() => { if (current) setLoading(false) })
    }, 220)
    return () => { current = false; window.clearTimeout(timer) }
  }, [query, token, hasLoadedSearchData])

  const term = query.trim().toLowerCase()
  const peopleResults: SearchResult[] = members.filter((person) => `${person.full_name} ${person.headline || ''} ${person.role}`.toLowerCase().includes(term)).slice(0, 3).map((person) => ({ key: person.id, kind: 'Person', title: person.full_name, detail: person.headline || roleName(person.role), icon: 'network', destination: 'My network', memberId: person.id }))
  const projectResults: SearchResult[] = remoteProjects.filter((project) => `${project.title} ${project.description} ${project.domain || ''} ${project.project_type}`.toLowerCase().includes(term)).slice(0, 3).map((project) => ({ key: project.id, kind: 'Project', title: project.title, detail: project.domain || roleName(project.project_type), icon: 'projects', destination: 'Projects' }))
  const mentorResults: SearchResult[] = remoteMentors.filter((mentor) => `${members.find((member) => member.id === mentor.user_id)?.full_name || ''} ${mentor.headline || ''} ${mentor.designation || ''} ${mentor.mentor_domains.join(' ')} ${mentor.mentoring_topics.join(' ')}`.toLowerCase().includes(term)).slice(0, 3).map((mentor) => ({ key: mentor.id, kind: 'Mentor', title: members.find((member) => member.id === mentor.user_id)?.full_name || 'CollabVerse mentor', detail: mentor.designation || mentor.headline || mentor.mentor_domains.join(' · '), icon: 'mentorship', destination: 'Mentorship', memberId: mentor.user_id }))
  const postResults: SearchResult[] = [...remotePosts, ...posts].filter((post, index, array) => array.findIndex((item) => item.id === post.id) === index && (post.content || '').toLowerCase().includes(term)).slice(0, 3).map((post) => ({ key: post.id, kind: 'Post', title: (post.content || 'Post').replace(/\s+/g, ' ').slice(0, 75), detail: `${post.like_count} appreciations · ${post.comment_count} comments`, icon: 'home', destination: 'Home' }))
  const results = term.length >= 2 ? [...peopleResults, ...projectResults, ...mentorResults, ...postResults] : []

  function choose(result: SearchResult) { if (result.memberId) onOpenProfile(result.memberId); else onNavigate(result.destination); setOpen(false); inputRef.current?.blur() }
  return <div className={`global-search-wrap ${open ? 'search-open' : ''}`}><label className="search-box"><Icon name="search" size={17} /><input ref={inputRef} value={query} onFocus={() => setOpen(true)} onChange={(event) => { setQuery(event.target.value); setOpen(true) }} placeholder="Search people, projects, mentors…" aria-label="Search CollabVerse" aria-expanded={open} aria-controls="global-search-results" /><kbd>⌘ K</kbd>{query && <button className="search-clear" aria-label="Clear search" onClick={() => setQuery('')}>×</button>}</label>{open && <><button className="global-search-dismiss" aria-label="Close search" onClick={() => setOpen(false)} /><section id="global-search-results" className="global-search-popover card" aria-label="Search results">{!term ? <div className="search-prompt"><span className="search-prompt-icon"><Icon name="search" size={18} /></span><strong>Search your professional community</strong><p>Find people, projects, mentors, and posts.</p><div><kbd>⌘ K</kbd><span>to focus</span><kbd>ESC</kbd><span>to close</span></div></div> : <><div className="search-results-heading"><span>Results for <strong>“{query.trim()}”</strong></span>{loading && <span className="search-spinner" />}</div>{results.length ? <div className="global-search-results-list">{results.map((result) => <button className="global-search-result" key={`${result.kind}-${result.key}`} onClick={() => choose(result)}><span className={`search-result-icon search-icon-${result.kind.toLowerCase()}`}><Icon name={result.icon} size={15} /></span><span className="search-result-copy"><strong>{result.title}</strong><small>{result.detail}</small></span><span className="search-result-kind">{result.kind}</span><span className="search-result-arrow">↗</span></button>)}</div> : <div className="search-no-results"><span className="search-prompt-icon"><Icon name="search" size={17} /></span><strong>{loading ? 'Searching CollabVerse…' : 'No matches yet'}</strong><p>{loading ? 'Looking across people, projects, mentors, and posts.' : 'Try another name, skill, or topic.'}</p></div>}</>}</section></>}</div>
}

type Message = { id: string; conversation_id: string; sender_id: string; content: string; is_edited: boolean; is_deleted: boolean; created_at: string }
type ConversationParticipant = { user_id: string }
type Conversation = { id: string; conversation_type: string; title?: string | null; participants: ConversationParticipant[]; last_message?: Message | null; unread_count: number; updated_at: string }

function ChatMessageContent({ content }: { content: string }) {
  const marker = /\[\[media:(image|video)\|(https?:\/\/[^\]\s]+)\]\]/g
  const parts: ReactNode[] = []
  let cursor = 0
  let match: RegExpExecArray | null
  while ((match = marker.exec(content)) !== null) {
    if (match.index > cursor) parts.push(<span key={`text-${cursor}`}>{content.slice(cursor, match.index)}</span>)
    const [, kind, url] = match
    parts.push(kind === 'video' ? <video className="chat-shared-video" key={match.index} src={url} controls preload="metadata" /> : <a className="chat-shared-image-link" key={match.index} href={url} target="_blank" rel="noreferrer"><img className="chat-shared-image" src={url} alt="Shared image" loading="lazy" /></a>)
    cursor = marker.lastIndex
  }
  if (cursor < content.length) parts.push(<span key={`text-${cursor}`}>{content.slice(cursor)}</span>)
  return <>{parts}</>
}

function MessagesScreen({ token, user, members, initialMemberId = '' }: { token: string; user: User; members: PublicUser[]; initialMemberId?: string }) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [draft, setDraft] = useState('')
  const [chatFiles, setChatFiles] = useState<File[]>([])
  const [chatUploading, setChatUploading] = useState(false)
  const [sending, setSending] = useState(false)
  const [search, setSearch] = useState('')
  const [notice, setNotice] = useState('')
  const transcriptRef = useState<HTMLDivElement | null>(null)
  const scrollRef = transcriptRef[0]
  const setScrollRef = transcriptRef[1]
  const selected = conversations.find((conversation) => conversation.id === selectedId)

  async function refreshConversations() {
    const data = await request<{ conversations: Conversation[] }>('/messaging/conversations?limit=100&offset=0', token)
    setConversations(data.conversations || [])
    setSelectedId((current) => current || data.conversations?.[0]?.id || '')
  }

  useEffect(() => {
    let live = true
    void request<{ conversations: Conversation[] }>('/messaging/conversations?limit=100&offset=0', token)
      .then(async (data) => {
        if (!live) return
        setConversations(data.conversations || [])
        if (initialMemberId) {
          const created = await request<Conversation>('/messaging/conversations/direct', token, { method: 'POST', body: JSON.stringify({ recipient_user_id: initialMemberId }) })
          if (live) { setSelectedId(created.id); setConversations((items) => items.some((item) => item.id === created.id) ? items : [created, ...items]) }
        } else setSelectedId(data.conversations?.[0]?.id || '')
      })
      .catch((reason) => { if (live) setNotice(reason instanceof Error ? reason.message : 'Could not load your conversations.') })
      .finally(() => { if (live) setLoading(false) })
    const timer = window.setInterval(() => { void refreshConversations().catch(() => {}) }, 15000)
    return () => { live = false; window.clearInterval(timer) }
  }, [token, initialMemberId])

  useEffect(() => {
    if (!selectedId) { setMessages([]); return }
    let live = true
    const load = () => request<{ messages: Message[] }>(`/messaging/conversations/${selectedId}/messages?limit=50&offset=0`, token)
      .then((data) => { if (live) setMessages((data.messages || []).slice().reverse()) })
      .catch((reason) => { if (live) setNotice(reason instanceof Error ? reason.message : 'Could not load this conversation.') })
    setMessagesLoading(true)
    void Promise.all([load(), request(`/messaging/conversations/${selectedId}/read`, token, { method: 'POST' }).catch(() => null)])
      .finally(() => { if (live) { setMessagesLoading(false); setConversations((items) => items.map((item) => item.id === selectedId ? { ...item, unread_count: 0 } : item)) } })
    const timer = window.setInterval(() => { void load() }, 8000)
    return () => { live = false; window.clearInterval(timer) }
  }, [selectedId, token])

  useEffect(() => { if (scrollRef) scrollRef.scrollTop = scrollRef.scrollHeight }, [messages, scrollRef])

  const displayName = (conversation: Conversation) => {
    if (conversation.title) return conversation.title
    const others = conversation.participants.filter((participant) => participant.user_id !== user.id)
    if (conversation.conversation_type === 'group') return others.map((person) => members.find((member) => member.id === person.user_id)?.full_name || 'Member').join(', ') || 'Group conversation'
    const otherId = others[0]?.user_id
    return members.find((member) => member.id === otherId)?.full_name || 'CollabVerse member'
  }
  const otherMember = (conversation: Conversation) => members.find((member) => member.id === conversation.participants.find((participant) => participant.user_id !== user.id)?.user_id)
  const visible = conversations.filter((conversation) => displayName(conversation).toLowerCase().includes(search.toLowerCase()) || (conversation.last_message?.content || '').toLowerCase().includes(search.toLowerCase()))

  async function send(event: FormEvent) {
    event.preventDefault()
    if ((!draft.trim() && !chatFiles.length) || !selectedId || sending) return
    setSending(true); setChatUploading(chatFiles.length > 0); setNotice('')
    try {
      let content = draft.trim()
      for (const file of chatFiles) {
        const uploaded = await uploadPostMedia(file, token)
        content += `${content ? '\n' : ''}[[media:${uploaded.media_type}|${uploaded.media_url}]]`
      }
      const created = await request<Message>(`/messaging/conversations/${selectedId}/messages`, token, { method: 'POST', body: JSON.stringify({ content }) })
      setMessages((current) => [...current, created]); setDraft(''); setChatFiles([]); void refreshConversations().catch(() => {})
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : 'Could not send this message.') }
    finally { setSending(false); setChatUploading(false) }
  }

  return <section className="messages-panel card">
    <aside className="messages-sidebar"><div className="messages-sidebar-top"><div><span className="eyebrow">YOUR INBOX</span><h2>Messages</h2></div><span className="inbox-count">{conversations.reduce((total, item) => total + item.unread_count, 0) || '—'}</span></div><label className="conversation-search"><Icon name="search" size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search messages" /></label>
      <div className="conversation-list">{loading ? <div className="message-empty"><span className="loading-spinner" /><p>Loading conversations…</p></div> : visible.length ? visible.map((conversation) => {
        const name = displayName(conversation)
        return <button key={conversation.id} className={`conversation-item ${selectedId === conversation.id ? 'conversation-selected' : ''}`} onClick={() => { setSelectedId(conversation.id); setNotice('') }}><Avatar name={name} imageUrl={otherMember(conversation)?.avatar_url} /><span className="conversation-copy"><strong>{name}</strong><small>{conversation.last_message?.content || 'Start the conversation'}</small></span><span className="conversation-meta"><small>{conversation.last_message ? timeAgo(conversation.last_message.created_at) : ''}</small>{conversation.unread_count > 0 && <b>{conversation.unread_count}</b>}</span></button>
      }) : <div className="message-empty"><span className="message-empty-icon"><Icon name="messages" size={21} /></span><strong>{search ? 'No matching conversations' : 'Your inbox is ready'}</strong><p>{search ? 'Try a different name or keyword.' : 'Conversations from mentorships and projects will appear here.'}</p></div>}</div>
    </aside>
    <div className="chat-pane">{selected ? <><header className="chat-header"><Avatar name={displayName(selected)} imageUrl={otherMember(selected)?.avatar_url} /><span><strong>{displayName(selected)}</strong><small>{roleName(otherMember(selected)?.role || selected.conversation_type)} · {roleName(selected.conversation_type)} conversation</small></span><button className="chat-header-action" title="Conversation details" aria-label="Conversation details"><Icon name="profile" size={17} /></button></header>
      <div className="chat-transcript" ref={setScrollRef}>{messagesLoading && messages.length === 0 ? <div className="message-empty"><span className="loading-spinner" /><p>Loading messages…</p></div> : messages.length === 0 ? <div className="message-empty"><span className="message-empty-icon"><Icon name="messages" size={21} /></span><strong>Start with a thoughtful message</strong><p>Share context and make it easy for the other person to reply.</p></div> : messages.map((message) => <div key={message.id} className={`message-row ${message.sender_id === user.id ? 'message-own' : ''}`}><div className="message-bubble"><p>{message.is_deleted ? 'This message was removed.' : <ChatMessageContent content={message.content} />}</p><small>{new Date(message.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}{message.is_edited ? ' · edited' : ''}</small></div></div>)}</div>
      <form className="message-compose" onSubmit={send}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Write a message…" rows={2} maxLength={5000} />{chatFiles.length > 0 && <div className="chat-file-list">{chatFiles.map((file, index) => <span key={`${file.name}-${index}`}>{file.name}<button type="button" aria-label={`Remove ${file.name}`} disabled={sending} onClick={() => setChatFiles((items) => items.filter((_, itemIndex) => itemIndex !== index))}>×</button></span>)}</div>}<div><label className="chat-media-picker" title="Attach photo or video"><Icon name="image" size={17} /><span>Media</span><input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" multiple disabled={sending} onChange={(event) => { const files = Array.from(event.currentTarget.files || []); setChatFiles((current) => [...current, ...files].slice(0, 5)); event.currentTarget.value = '' }} /></label><span>{chatUploading ? 'Uploading media…' : 'Photos up to 10 MB · videos up to 100 MB'}</span><button className="primary-button" disabled={(!draft.trim() && !chatFiles.length) || sending}>{sending ? chatUploading ? 'Uploading…' : 'Sending…' : 'Send'} <span>↗</span></button></div></form>
    </> : <div className="chat-welcome"><div className="message-empty-icon"><Icon name="messages" size={26} /></div><h2>{loading ? 'Opening your inbox…' : 'Professional conversations, all in one place'}</h2><p>Choose a conversation to catch up. Mentorship and project conversations will show up here.</p></div>}</div>
    {notice && <div className="messages-notice" role="status">{notice}<button onClick={() => setNotice('')}>×</button></div>}
  </section>
}

type PublicProfileData = { user_id: string; role: string; avatar_url?: string | null; full_name: string; headline?: string | null; profile: Record<string, unknown>; interests: string[]; goals: string[]; mentor_profile?: Record<string, unknown> | null; projects: { id: string; title: string; description: string; domain?: string | null; project_type: string; status: string; role: string; updated_at: string }[] }

function PublicProfileScreen({ token, user, memberId, members, onBack, onMessage }: { token: string; user: User; memberId: string; members: PublicUser[]; onBack: () => void; onMessage: (memberId: string) => void }) {
  const [data, setData] = useState<PublicProfileData | null>(null)
  const [uploads, setUploads] = useState<Post[]>([])
  const [connection, setConnection] = useState<Connection | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => {
    let current = true
    void Promise.all([
      request<PublicProfileData>(`/users/${memberId}/profile`, token),
      request<Post[]>(`/posts/users/${memberId}?limit=30&offset=0`, token).catch(() => []),
      request<Connection[]>('/connections', token).catch(() => []),
      request<Connection[]>('/connections/requests/incoming', token).catch(() => []),
      request<Connection[]>('/connections/requests/outgoing', token).catch(() => []),
    ]).then(([profile, posts, accepted, incoming, outgoing]) => {
      if (!current) return
      setData(profile)
      setUploads(posts)
      setConnection([...accepted, ...incoming, ...outgoing].find((item) => item.requester_id === memberId && item.recipient_id === user.id || item.requester_id === user.id && item.recipient_id === memberId) || null)
    }).catch((reason) => { if (current) setError(reason instanceof Error ? reason.message : 'Could not load this member profile.') })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [token, memberId, user.id])

  async function connectionAction(action: 'connect' | 'accept' | 'reject') {
    setBusy(true); setError(''); setNotice('')
    try {
      const path = action === 'connect' ? `/connections/${memberId}` : `/connections/${connection?.id}/${action}`
      const result = await request<Connection>(path, token, { method: action === 'connect' ? 'POST' : 'PATCH' })
      setConnection(result)
      setNotice(action === 'connect' ? 'Connection invitation sent.' : action === 'accept' ? 'You’re now connected.' : 'Invitation declined.')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update this connection.') }
    finally { setBusy(false) }
  }

  const profile = data?.profile || {}
  const text = (key: string) => typeof profile[key] === 'string' ? String(profile[key]) : ''
  const list = (key: string) => Array.isArray(profile[key]) ? (profile[key] as unknown[]).filter((item): item is string => typeof item === 'string' && !!item.trim()) : []
  const label = (key: string) => key.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
  const skipFields = new Set(['full_name', 'admin_name', 'headline', 'bio', 'research_interests', 'professional_interests', 'goals', 'linkedin_url', 'portfolio_url', 'github_url', 'company_website', 'website', 'organization_id', 'established_date'])
  const details = Object.entries(profile).filter(([key, value]) => !skipFields.has(key) && (typeof value === 'string' || typeof value === 'number') && value !== '').map(([key, value]) => [label(key), String(value)] as const)
  const interests = [...new Set([...((data?.interests || [])), ...list('professional_interests'), ...text('research_interests').split(/[,;\n]/).map((item) => item.trim()).filter(Boolean)])]
  const goals = [...new Set([...(data?.goals || []), ...list('goals'), text('career_goal')].filter(Boolean))]
  const about = text('bio') || text('research_interests') || (text('career_goal') ? `Career goal: ${text('career_goal')}` : '')
  const relationship = connection
  const publicLinks = [['LinkedIn', text('linkedin_url')], ['Portfolio', text('portfolio_url')], ['GitHub', text('github_url')], ['Organization website', text('company_website') || text('website')]].filter(([, value]) => value) as [string, string][]
  const mentor = data?.mentor_profile

  if (loading) return <div className="public-profile-loading card"><span className="loading-spinner" /><p>Loading member profile…</p></div>
  if (!data) return <section className="public-profile-page"><button className="project-back-link" onClick={onBack}>← Back</button><div className="inline-error">{error || 'This profile is not available.'}</div></section>

  return <section className="public-profile-page"><button className="project-back-link" onClick={onBack}><span>←</span> Back</button>
    <header className="public-profile-hero card"><div className="public-profile-cover"><div className="public-profile-orbit"><span>✳</span><i /></div></div><div className="public-profile-identity"><Avatar name={data.full_name} large imageUrl={data.avatar_url} /><div className="public-profile-title"><span className="role-pill">{roleName(data.role)}</span><h2>{data.full_name}</h2><p>{data.headline || `${roleName(data.role)} · CollabVerse`}</p></div><div className="public-profile-actions">{relationship?.status === 'accepted' && <button className="primary-button" onClick={() => onMessage(memberId)}><Icon name="messages" size={14} /> Message</button>}{relationship?.status === 'accepted' ? <button className="connected-profile-button" disabled>✓ Connected</button> : relationship?.status === 'pending' && relationship.requester_id === user.id ? <button className="connected-profile-button" disabled>Invitation sent</button> : relationship?.status === 'pending' ? <><button className="primary-button" disabled={busy} onClick={() => void connectionAction('accept')}>{busy ? 'Working…' : 'Accept invitation'}</button><button className="profile-decline-button" disabled={busy} onClick={() => void connectionAction('reject')}>Decline</button></> : <button className="primary-button" disabled={busy} onClick={() => void connectionAction('connect')}>{busy ? 'Sending…' : '+ Connect'}</button>}</div></div>{(error || notice) && <div className={error ? 'profile-feedback profile-feedback-error' : 'profile-feedback'}>{error || notice}<button onClick={() => { setError(''); setNotice('') }}>×</button></div>}</header>
    <div className="public-profile-layout"><div className="public-profile-main">{about && <article className="public-profile-section card"><span className="eyebrow">ABOUT</span><h3>A little about {data.full_name.split(' ')[0]}</h3><p>{about}</p></article>}{details.length > 0 && <article className="public-profile-section card"><span className="eyebrow">BACKGROUND</span><h3>Experience & education</h3><div className="public-profile-details">{details.map(([key, value]) => <div key={key}><small>{key}</small><strong>{value}</strong></div>)}</div></article>}{uploads.length > 0 && <article className="public-profile-section card"><div className="public-profile-section-heading"><div><span className="eyebrow">SHARED WITH THE COMMUNITY</span><h3>Posts & uploads</h3></div><span>{uploads.length}</span></div><div className="public-upload-list">{uploads.map((post) => <article className="public-upload" key={post.id}>{post.content && <p>{post.content}</p>}{post.media?.length ? <div className="public-upload-media">{post.media.map((media) => media.media_type === 'video' ? <video key={media.id} src={media.media_url} controls /> : <img key={media.id} src={media.media_url} alt="Post upload" loading="lazy" />)}</div> : null}<small>{timeAgo(post.created_at)}</small></article>)}</div></article>}{data.projects.length > 0 && <article className="public-profile-section card"><div className="public-profile-section-heading"><div><span className="eyebrow">COLLABORATION</span><h3>Public projects</h3></div><span>{data.projects.length}</span></div><div className="public-project-list">{data.projects.map((project) => <div className="public-project" key={project.id}><span className="public-project-icon"><Icon name="projects" size={16} /></span><div><strong>{project.title}</strong><small>{project.domain || roleName(project.project_type)} · {roleName(project.role)} · {roleName(project.status)}</small><p>{project.description}</p></div></div>)}</div></article>}</div>
      <aside className="public-profile-side">{interests.length > 0 && <article className="public-profile-section card"><span className="eyebrow">AREAS OF INTEREST</span><h3>Curious about</h3><div className="public-interest-tags">{interests.map((interest) => <span key={interest}>{interest}</span>)}</div></article>}{goals.length > 0 && <article className="public-profile-section card"><span className="eyebrow">PROFESSIONAL GOALS</span><h3>What they’re working toward</h3><div className="public-interest-tags">{goals.map((goal) => <span key={goal}>{goal}</span>)}</div></article>}{mentor && <article className="public-profile-section public-mentor-card card"><div className="public-mentor-heading"><span className="public-project-icon"><Icon name="mentorship" size={16} /></span><div><span className="eyebrow">MENTORSHIP</span><h3>{mentor.is_accepting_mentees ? 'Available as a mentor' : 'Mentor profile'}</h3></div></div><p>{String(mentor.headline || mentor.bio || 'Open to supporting others in their professional journey.')}</p>{Array.isArray(mentor.mentor_domains) && <div className="public-interest-tags">{(mentor.mentor_domains as string[]).map((item) => <span key={item}>{item}</span>)}</div>}{Array.isArray(mentor.mentoring_topics) && <div className="public-mentor-topics"><small>CAN HELP WITH</small><strong>{(mentor.mentoring_topics as string[]).join(' · ') || 'Career development'}</strong></div>}<div className="public-mentor-availability">{String(mentor.mentoring_mode || 'online')} · {mentor.is_accepting_mentees ? 'Accepting mentees' : 'Not accepting currently'}</div></article>}{publicLinks.length > 0 && <article className="public-profile-section card"><span className="eyebrow">ELSEWHERE</span><h3>Professional links</h3><div className="public-profile-links">{publicLinks.map(([title, href]) => <a href={href.startsWith('http') ? href : `https://${href}`} target="_blank" rel="noreferrer" key={title}>{title}<span>↗</span></a>)}</div></article>}</aside></div>
  </section>
}

type Project = { id: string; creator_id: string; title: string; description: string; domain?: string | null; project_type: string; difficulty: string; status: string; visibility: string; max_team_size?: number | null; is_accepting_members: boolean; start_date?: string | null; end_date?: string | null; created_at: string; skills?: { id: string; skill_id: string; required_level?: number | null }[] }
type ProjectResource = { id: string; project_id: string; added_by: string; title: string; resource_type: 'repository' | 'document' | 'media' | 'link'; url: string; description?: string | null; file_name?: string | null; content_type?: string | null; created_at: string }

function ProjectsScreen({ token, user, members, initialTab = 'discover' }: { token: string; user: User; members: PublicUser[]; initialTab?: 'discover' | 'created' | 'joined' }) {
  const [tab, setTab] = useState<'discover' | 'created' | 'joined'>(initialTab)
  const [projects, setProjects] = useState<Project[]>([])
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [search, setSearch] = useState('')
  const [domain, setDomain] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [busyId, setBusyId] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  async function loadProjects(selectedTab = tab) {
    setLoadingProjects(true); setError('')
    try {
      const path = selectedTab === 'created' ? '/projects/me/created' : selectedTab === 'joined' ? '/projects/me/joined' : '/projects?limit=50&skip=0&status=open'
      const data = await request<Project[]>(path, token)
      setProjects(data || [])
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load projects.') }
    finally { setLoadingProjects(false) }
  }
  useEffect(() => { void loadProjects(tab) }, [tab, token])

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusyId('create'); setError(''); setNotice('')
    const form = new FormData(event.currentTarget)
    const payload = { title: String(form.get('title') || '').trim(), description: String(form.get('description') || '').trim(), domain: String(form.get('domain') || '').trim() || null, project_type: String(form.get('project_type') || 'open_collaboration'), difficulty: String(form.get('difficulty') || 'beginner'), visibility: 'public', max_team_size: Number(form.get('max_team_size') || 5), is_accepting_members: true }
    try {
      const created = await request<Project>('/projects', token, { method: 'POST', body: JSON.stringify(payload) })
      setShowCreate(false); setTab('created'); setSelectedProjectId(created.id); setNotice('Your project is live. You can manage it from My projects.');
      if (tab === 'created') await loadProjects('created')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not create your project.') }
    finally { setBusyId('') }
  }

  const filtered = projects.filter((project) => {
    const query = search.trim().toLowerCase()
    return (!query || `${project.title} ${project.description} ${project.domain || ''}`.toLowerCase().includes(query)) && (!domain || project.domain?.toLowerCase().includes(domain.toLowerCase()))
  })
  const format = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
  const dateLabel = (value?: string | null) => value ? new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : ''

  if (selectedProjectId) return <ProjectWorkspace token={token} user={user} members={members} projectId={selectedProjectId} onBack={() => setSelectedProjectId('')} onChanged={() => void loadProjects(tab)} />

  return <section className="projects-page">
    <div className="projects-banner"><div className="projects-banner-art"><span>✳</span><i /><i /><i /></div><div className="projects-banner-copy"><span className="eyebrow">BUILD SOMETHING MEANINGFUL</span><h2>Good work starts with the right team.</h2><p>Find research, academic, and industry collaborations—or bring your own idea to life.</p></div><button className="primary-button" onClick={() => { setShowCreate((value) => !value); setError('') }}>{showCreate ? 'Close form' : '＋ Create a project'}</button></div>
    {error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}{notice && <div className="project-notice">{notice}<button onClick={() => setNotice('')}>×</button></div>}
    {showCreate && <form className="project-create-card card" onSubmit={(event) => void createProject(event)}><div className="project-form-heading"><div><span className="eyebrow">START A COLLABORATION</span><h2>Create a project</h2></div><button type="button" className="project-close" onClick={() => setShowCreate(false)} aria-label="Close form">×</button></div><label className="project-field">Project title<input name="title" required maxLength={255} placeholder="e.g. Open-source climate data toolkit" /></label><label className="project-field">What are you building?<textarea name="description" required rows={3} placeholder="Describe the goal, the work, and who you hope to collaborate with." /></label><div className="project-form-grid"><label className="project-field">Domain<input name="domain" placeholder="e.g. Climate science" /></label><label className="project-field">Project type<select name="project_type"><option value="open_collaboration">Open collaboration</option><option value="research">Research</option><option value="academic">Academic</option><option value="industry_live">Industry project</option><option value="student">Student project</option><option value="startup">Startup</option><option value="hackathon">Hackathon</option><option value="innovation_challenge">Innovation challenge</option></select></label><label className="project-field">Experience level<select name="difficulty"><option value="beginner">Beginner friendly</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><label className="project-field">Team size<input name="max_team_size" type="number" min="1" max="100" defaultValue="5" /></label></div><div className="project-form-footer"><span>Public projects can be discovered by the community.</span><button className="primary-button" disabled={busyId === 'create'}>{busyId === 'create' ? 'Creating…' : 'Publish project'} <span>↗</span></button></div></form>}
    <div className="projects-controls"><div className="project-tabs"><button className={tab === 'discover' ? 'project-tab-active' : ''} onClick={() => setTab('discover')}>Discover</button><button className={tab === 'created' ? 'project-tab-active' : ''} onClick={() => setTab('created')}>My projects</button><button className={tab === 'joined' ? 'project-tab-active' : ''} onClick={() => setTab('joined')}>Joined</button></div><div className="project-filters"><label className="project-search"><Icon name="search" size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search projects" /></label><label className="domain-filter"><span>Domain</span><input value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="Any domain" /></label></div></div>
    <div className="projects-results-heading"><div><h2>{tab === 'discover' ? 'Explore projects' : tab === 'created' ? 'Projects you created' : 'Projects you’ve joined'}</h2><p>{tab === 'discover' ? 'Open opportunities to learn, contribute, and collaborate.' : 'Keep track of your collaborations and next steps.'}</p></div><span>{filtered.length} {filtered.length === 1 ? 'project' : 'projects'}</span></div>
    {loadingProjects ? <div className="projects-loading card"><span className="loading-spinner" /><p>Finding projects for you…</p></div> : filtered.length ? <div className="project-grid">{filtered.map((project) => <article className="project-card card" key={project.id}><div className="project-card-top"><span className={`project-type-icon project-type-${project.project_type}`}><Icon name="projects" size={19} /></span><span className={`project-status status-${project.status}`}>{format(project.status)}</span></div><div className="project-tags"><span>{format(project.project_type)}</span>{project.domain && <span>{project.domain}</span>}</div><h3>{project.title}</h3><p className="project-description">{project.description}</p><div className="project-card-meta"><span><i className="project-meta-dot" />{format(project.difficulty)}</span>{project.max_team_size && <span><Icon name="network" size={13} /> Team of up to {project.max_team_size}</span>}</div>{(project.start_date || project.end_date) && <div className="project-dates">{project.start_date ? `Starts ${dateLabel(project.start_date)}` : ''}{project.start_date && project.end_date ? ' · ' : ''}{project.end_date ? `Due ${dateLabel(project.end_date)}` : ''}</div>}<div className="project-card-footer"><span><Avatar name={project.creator_id === user.id ? user.profile?.full_name || user.email : 'CollabVerse member'} /><span><strong>{project.creator_id === user.id ? 'You' : 'Project team'}</strong><small>{project.creator_id === user.id ? 'Project lead' : 'Community project'}</small></span></span><button className="project-view-button" onClick={() => setSelectedProjectId(project.id)}>{tab === 'created' || tab === 'joined' || project.creator_id === user.id ? 'Open workspace' : 'View project'} <span>→</span></button></div></article>)}</div> : <div className="projects-empty card"><span className="message-empty-icon"><Icon name="projects" size={22} /></span><h3>{search || domain ? 'No projects match those filters' : tab === 'discover' ? 'No open projects just yet' : tab === 'created' ? 'Your projects will appear here' : 'You haven’t joined a project yet'}</h3><p>{search || domain ? 'Adjust the search or domain and give it another try.' : tab === 'discover' ? 'Check back soon, or create the first collaboration for your community.' : tab === 'created' ? 'Launch a project and invite your community to contribute.' : 'Explore open projects and apply to work with a team.'}</p>{!search && !domain && (tab === 'discover' || tab === 'created') && <button className="primary-button" onClick={() => setShowCreate(true)}>Create a project <span>↗</span></button>}</div>}
  </section>
}

type Mentor = { id: string; user_id: string; headline?: string | null; bio?: string | null; designation?: string | null; years_of_experience?: number | null; mentor_domains: string[]; mentoring_topics: string[]; mentoring_mode: string; location?: string | null; is_accepting_mentees: boolean; max_mentees?: number | null; is_verified: boolean }
type Mentorship = { id: string; mentor_profile_id: string; mentee_user_id: string; request_message?: string | null; goals?: string | null; status: string; response_message?: string | null; requested_at: string; started_at?: string | null }

function ProjectWorkspace({ token, user, members, projectId, onBack, onChanged }: { token: string; user: User; members: PublicUser[]; projectId: string; onBack: () => void; onChanged: () => void }) {
  const [project, setProject] = useState<Project | null>(null)
  const [team, setTeam] = useState<{ id: string; user_id: string; role: string; joined_at: string }[]>([])
  const [resources, setResources] = useState<ProjectResource[]>([])
  const [applications, setApplications] = useState<{ id: string; user_id: string; message?: string | null; status: string; applied_at: string }[]>([])
  const [application, setApplication] = useState<{ id: string; status: string } | null>(null)
  const [tab, setTab] = useState<'overview' | 'resources' | 'team' | 'applications'>('overview')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [applyOpen, setApplyOpen] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [resourceKind, setResourceKind] = useState<'repository' | 'document' | 'link'>('repository')
  const [uploadingResources, setUploadingResources] = useState(false)
  const resourceFileInput = useRef<HTMLInputElement>(null)
  const owner = project?.creator_id === user.id
  const joined = team.some((member) => member.user_id === user.id)
  const canShareResources = Boolean(owner || joined)

  async function loadWorkspace() {
    setLoading(true); setError('')
    try {
      const [projectData, teamData] = await Promise.all([
        request<Project>(`/projects/${projectId}`, token),
        request<{ id: string; user_id: string; role: string; joined_at: string }[]>(`/projects/${projectId}/members`, token),
      ])
      setProject(projectData); setTeam(teamData || [])
      if (projectData.creator_id === user.id || teamData.some((member) => member.user_id === user.id)) {
        setResources(await request<ProjectResource[]>(`/projects/${projectId}/resources`, token))
      } else setResources([])
      if (projectData.creator_id === user.id) {
        const apps = await request<{ id: string; user_id: string; message?: string | null; status: string; applied_at: string }[]>(`/projects/${projectId}/applications`, token)
        setApplications(apps || [])
      } else setApplications([])
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not open this project workspace.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void loadWorkspace() }, [token, projectId])

  async function submitApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!project) return
    const form = new FormData(event.currentTarget); setBusy('apply'); setError(''); setNotice('')
    try {
      const result = await request<{ id: string; status: string }>(`/projects/${projectId}/apply`, token, { method: 'POST', body: JSON.stringify({ message: String(form.get('message') || '').trim() || null }) })
      setApplication(result); setApplyOpen(false); setNotice('Your application has been sent to the project lead.')
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Could not submit your application.'
      if (/already applied/i.test(message)) setApplication({ id: '', status: 'pending' })
      setError(message)
    } finally { setBusy('') }
  }

  async function applicationDecision(applicationId: string, action: 'accept' | 'reject') {
    setBusy(applicationId); setError(''); setNotice('')
    try {
      await request(`/projects/${projectId}/applications/${applicationId}/${action}`, token, { method: 'POST' })
      setNotice(action === 'accept' ? 'Applicant accepted and added to your team.' : 'Application declined.')
      await loadWorkspace(); onChanged()
    } catch (reason) { setError(reason instanceof Error ? reason.message : `Could not ${action} this application.`) }
    finally { setBusy('') }
  }

  async function updateProject(payload: Partial<Project>, label: string) {
    if (!project) return
    setBusy('project'); setError(''); setNotice('')
    try {
      const updated = await request<Project>(`/projects/${projectId}`, token, { method: 'PUT', body: JSON.stringify(payload) })
      setProject(updated); setNotice(label); onChanged()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update the project.') }
    finally { setBusy('') }
  }

  async function addWorkspaceLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    setBusy('resource'); setError(''); setNotice('')
    try {
      const resource = await request<ProjectResource>(`/projects/${projectId}/resources`, token, { method: 'POST', body: JSON.stringify({ title: String(data.get('title') || '').trim(), url: String(data.get('url') || '').trim(), description: String(data.get('description') || '').trim() || null, resource_type: resourceKind }) })
      setResources((items) => [resource, ...items]); form.reset(); setNotice('Shared with the project team.')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not share this link.') }
    finally { setBusy('') }
  }

  async function uploadWorkspaceFiles(files: FileList | null) {
    if (!files?.length) return
    setUploadingResources(true); setError(''); setNotice('')
    try {
      const added: ProjectResource[] = []
      for (const file of Array.from(files)) {
        const body = new FormData(); body.append('file', file); body.append('title', file.name)
        let response: Response
        try { response = await fetch(`${API}/projects/${projectId}/resources/upload`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body }) }
        catch { throw new Error('Could not reach the project upload service.') }
        if (!response.ok) { const result = await response.json().catch(() => null); throw new Error(result?.detail || `Could not upload ${file.name}.`) }
        added.push(await response.json())
      }
      setResources((items) => [...added.reverse(), ...items]); setNotice(`${added.length} ${added.length === 1 ? 'file' : 'files'} shared with the project team.`)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not upload these files.') }
    finally { setUploadingResources(false); if (resourceFileInput.current) resourceFileInput.current.value = '' }
  }

  async function removeWorkspaceResource(resource: ProjectResource) {
    setBusy(resource.id); setError('')
    try { await request(`/projects/${projectId}/resources/${resource.id}`, token, { method: 'DELETE' }); setResources((items) => items.filter((item) => item.id !== resource.id)); setNotice('Shared resource removed.') }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not remove this resource.') }
    finally { setBusy('') }
  }

  async function removeMember(memberUserId: string) {
    if (!window.confirm(`Remove ${personName(memberUserId)} from this project?`)) return
    setBusy(memberUserId); setError(''); setNotice('')
    try {
      await request(`/projects/${projectId}/members/${memberUserId}`, token, { method: 'DELETE' })
      setTeam((current) => current.filter((member) => member.user_id !== memberUserId)); setNotice('Team member removed.'); onChanged()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not remove this team member.') }
    finally { setBusy('') }
  }

  async function leaveProject() {
    if (!window.confirm('Leave this project team?')) return
    setBusy('leave'); setError('')
    try { await request(`/projects/${projectId}/leave`, token, { method: 'DELETE' }); setNotice('You left the project.'); onBack(); onChanged() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not leave this project.') }
    finally { setBusy('') }
  }

  function personName(id: string) { return id === user.id ? user.profile?.full_name || user.email.split('@')[0] : members.find((member) => member.id === id)?.full_name || 'CollabVerse member' }
  const format = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
  const displayDate = (value?: string | null) => value ? new Date(value).toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' }) : 'Not set'
  const pendingApplications = applications.filter((item) => item.status === 'pending')

  if (loading && !project) return <section className="project-workspace"><button className="project-back-link" onClick={onBack}>← Back to projects</button><div className="projects-loading card"><span className="loading-spinner" /><p>Opening project workspace…</p></div></section>
  if (!project) return <section className="project-workspace"><button className="project-back-link" onClick={onBack}>← Back to projects</button><div className="inline-error">{error || 'Project not found.'}</div></section>

  return <section className="project-workspace"><button className="project-back-link" onClick={onBack}><span>←</span> Back to projects</button>
    <header className="project-workspace-hero"><div className="project-workspace-icon"><Icon name="projects" size={23} /></div><div className="project-workspace-title"><div className="project-workspace-tags"><span>{format(project.project_type)}</span>{project.domain && <span>{project.domain}</span>}<span className={`project-status status-${project.status}`}>{format(project.status)}</span></div><h2>{project.title}</h2><p>Led by {personName(project.creator_id)} · Created {displayDate(project.created_at)}</p></div>{owner && <label className="workspace-status-field"><small>PROJECT STATUS</small><select value={project.status} disabled={busy === 'project'} onChange={(event) => void updateProject({ status: event.target.value }, 'Project status updated.')}><option value="draft">Draft</option><option value="open">Open</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></label>}</header>
    {error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}{notice && <div className="project-notice">{notice}<button onClick={() => setNotice('')}>×</button></div>}
    <div className="workspace-tabs"><button className={tab === 'overview' ? 'workspace-tab-active' : ''} onClick={() => setTab('overview')}>Overview</button>{canShareResources && <button className={tab === 'resources' ? 'workspace-tab-active' : ''} onClick={() => setTab('resources')}>Workspace <span>{resources.length}</span></button>}<button className={tab === 'team' ? 'workspace-tab-active' : ''} onClick={() => setTab('team')}>Team <span>{team.length}</span></button>{owner && <button className={tab === 'applications' ? 'workspace-tab-active' : ''} onClick={() => setTab('applications')}>Applications <span>{pendingApplications.length || applications.length}</span></button>}</div>
    {tab === 'overview' && <div className="workspace-overview"><article className="workspace-main-card card"><div className="workspace-card-heading"><div><span className="eyebrow">PROJECT BRIEF</span><h3>About this project</h3></div><span className="workspace-difficulty">{format(project.difficulty)}</span></div><p className="workspace-description">{project.description}</p><div className="workspace-facts"><div><small>PROJECT TYPE</small><strong>{format(project.project_type)}</strong></div><div><small>DOMAIN</small><strong>{project.domain || 'Open domain'}</strong></div><div><small>TEAM SIZE</small><strong>{team.length}{project.max_team_size ? ` / ${project.max_team_size}` : ''} members</strong></div><div><small>START DATE</small><strong>{displayDate(project.start_date)}</strong></div><div><small>END DATE</small><strong>{displayDate(project.end_date)}</strong></div><div><small>VISIBILITY</small><strong>{format(project.visibility)}</strong></div></div></article><aside className="workspace-side-card card"><div className="workspace-card-heading"><div><span className="eyebrow">COLLABORATION</span><h3>Build the team</h3></div></div><div className="workspace-team-preview">{team.slice(0, 5).map((member) => <div key={member.id}><Avatar name={personName(member.user_id)} /><span><strong>{personName(member.user_id)}</strong><small>{format(member.role)}</small></span></div>)}</div><button className="workspace-text-link" onClick={() => setTab('team')}>View all {team.length} team members <span>→</span></button>{owner ? <div className="workspace-owner-controls"><label><input type="checkbox" checked={project.is_accepting_members} disabled={busy === 'project'} onChange={(event) => void updateProject({ is_accepting_members: event.target.checked }, event.target.checked ? 'This project is now accepting members.' : 'Applications are paused.')} /><span>Accepting applications</span></label><small>Turn this off to pause new applications.</small></div> : joined ? <button className="workspace-leave-button" disabled={busy === 'leave'} onClick={() => void leaveProject()}>{busy === 'leave' ? 'Leaving…' : 'Leave project'}</button> : <>{application ? <div className="workspace-application-state"><span>✓</span><div><strong>Application {format(application.status)}</strong><small>The project lead will be notified.</small></div></div> : project.is_accepting_members && project.status === 'open' ? <button className="primary-button workspace-apply-cta" onClick={() => setApplyOpen((value) => !value)}>{applyOpen ? 'Close application' : 'Apply to join'} <span>↗</span></button> : <div className="workspace-closed-note">This project is not accepting applications right now.</div>}</>}</aside>
      {applyOpen && <form className="workspace-application-form card" onSubmit={(event) => void submitApplication(event)}><div className="workspace-card-heading"><div><span className="eyebrow">YOUR APPLICATION</span><h3>Introduce yourself</h3></div></div><p>Tell the project lead what you’d like to contribute or learn.</p><textarea name="message" maxLength={2000} rows={4} placeholder="Share relevant experience, skills, and what interests you about this project." /><div className="project-form-footer"><span>Applications are private to the project team.</span><button className="primary-button" disabled={busy === 'apply'}>{busy === 'apply' ? 'Sending…' : 'Submit application'} <span>↗</span></button></div></form>}</div>}
    {tab === 'team' && <div className="workspace-team-section"><div className="workspace-section-heading"><div><h3>Project team</h3><p>People collaborating on this project.</p></div><span>{team.length} {team.length === 1 ? 'member' : 'members'}{project.max_team_size ? ` · ${project.max_team_size} max` : ''}</span></div><div className="workspace-member-list">{team.map((member) => <article className="workspace-member card" key={member.id}><Avatar name={personName(member.user_id)} /><span><strong>{personName(member.user_id)}</strong><small>{member.user_id === user.id ? 'You · ' : ''}{format(member.role)} · Joined {new Date(member.joined_at).toLocaleDateString([], { month: 'short', year: 'numeric' })}</small></span>{member.role === 'owner' && <span className="workspace-owner-badge">Project lead</span>}{owner && member.user_id !== user.id && <button className="workspace-remove-member" disabled={busy === member.user_id} onClick={() => void removeMember(member.user_id)}>Remove</button>}</article>)}</div>{!team.length && <div className="projects-empty card"><h3>Your team is taking shape</h3><p>Accepted applicants will appear here.</p></div>}</div>}
    {tab === 'resources' && canShareResources && <div className="project-shared-workspace"><div className="workspace-section-heading"><div><h3>Shared workspace</h3><p>Keep repositories, useful links, documents, and project media together for your team.</p></div><span>{resources.length} shared</span></div><div className="workspace-share-grid"><form className="workspace-share-link card" onSubmit={(event) => void addWorkspaceLink(event)}><span className="eyebrow">ADD A SHARED LINK</span><label className="project-field">What are you sharing?<select value={resourceKind} onChange={(event) => setResourceKind(event.target.value as typeof resourceKind)}><option value="repository">Code repository</option><option value="document">Document or design</option><option value="link">Reference link</option></select></label><label className="project-field">Title<input name="title" required maxLength={255} placeholder="e.g. GitHub repository" /></label><label className="project-field">URL<input name="url" type="url" required placeholder="https://github.com/your-team/project" /></label><label className="project-field">Notes<textarea name="description" rows={2} maxLength={2000} placeholder="What should teammates know about this link?" /></label><button className="primary-button" disabled={busy === 'resource'}>{busy === 'resource' ? 'Sharing…' : 'Share link'} <span>↗</span></button></form><article className="workspace-share-upload card"><span className="eyebrow">UPLOAD TEAM FILES</span><h3>Share media and documents</h3><p>Upload images, videos, or PDFs for project members. Files are stored with your configured upload provider.</p><input ref={resourceFileInput} type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,application/pdf" multiple hidden onChange={(event) => void uploadWorkspaceFiles(event.currentTarget.files)} /><button className="secondary-button" onClick={() => resourceFileInput.current?.click()} disabled={uploadingResources}>{uploadingResources ? 'Uploading…' : 'Choose files'} <span>＋</span></button><small>JPG, PNG, WebP, MP4, WebM, or PDF. Up to 20 MB per file; videos up to 100 MB.</small></article></div><div className="workspace-resource-list">{resources.map((resource) => <article className="workspace-resource card" key={resource.id}>{resource.content_type?.startsWith('image/') && <a href={resource.url} target="_blank" rel="noreferrer" className="workspace-resource-preview"><img src={resource.url} alt={resource.title} loading="lazy" /></a>}{resource.content_type?.startsWith('video/') && <video className="workspace-resource-preview" src={resource.url} controls preload="metadata" />}{resource.content_type === 'application/pdf' && <span className="workspace-resource-file-mark">PDF</span>}<div className="workspace-resource-copy"><span className="workspace-resource-type">{resource.resource_type === 'repository' ? '⌘ REPOSITORY' : resource.resource_type.toUpperCase()}</span><a href={resource.url} target="_blank" rel="noreferrer"><strong>{resource.title}</strong><span>↗</span></a>{resource.description && <p>{resource.description}</p>}<small>Shared by {personName(resource.added_by)} · {timeAgo(resource.created_at)}{resource.file_name ? ` · ${resource.file_name}` : ''}</small></div>{(owner || resource.added_by === user.id) && <button className="remove-item workspace-resource-remove" aria-label={`Remove ${resource.title}`} disabled={busy === resource.id} onClick={() => void removeWorkspaceResource(resource)}>×</button>}</article>)}{resources.length === 0 && <div className="projects-empty card"><span className="message-empty-icon"><Icon name="projects" size={21} /></span><h3>Your project resources will live here</h3><p>Share the repository, reference material, and files your team needs to work together.</p></div>}</div></div>}
    {tab === 'applications' && owner && <div className="workspace-applications"><div className="workspace-section-heading"><div><h3>Applications</h3><p>Review people who want to contribute to your project.</p></div><span>{pendingApplications.length} pending · {applications.length} total</span></div>{applications.length ? <div className="workspace-application-list">{applications.map((item) => <article className="workspace-applicant card" key={item.id}><Avatar name={personName(item.user_id)} /><div><strong>{personName(item.user_id)}</strong><small>Applied {new Date(item.applied_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}</small><p>{item.message || 'No introduction provided.'}</p></div><span className={`mentorship-status mentorship-${item.status}`}>{format(item.status)}</span>{item.status === 'pending' && <div className="workspace-applicant-actions"><button className="primary-button" disabled={busy === item.id} onClick={() => void applicationDecision(item.id, 'accept')}>Accept</button><button className="decline-request" disabled={busy === item.id} onClick={() => void applicationDecision(item.id, 'reject')}>Decline</button></div>}</article>)}</div> : <div className="projects-empty card"><span className="message-empty-icon"><Icon name="network" size={21} /></span><h3>No applications yet</h3><p>When people apply, you’ll be able to review their introductions and invite them to the team here.</p></div>}</div>}
  </section>
}

function MentorshipScreen({ token, user, members, onMessage }: { token: string; user: User; members: PublicUser[]; onMessage: (memberId: string) => void }) {
  const [tab, setTab] = useState<'discover' | 'my requests' | 'active'>('discover')
  const [mentors, setMentors] = useState<Mentor[]>([])
  const [sent, setSent] = useState<Mentorship[]>([])
  const [received, setReceived] = useState<Mentorship[]>([])
  const [activeMentors, setActiveMentors] = useState<{ mentorship_id: string; mentor: Mentor; goals?: string | null; started_at?: string | null }[]>([])
  const [activeMentees, setActiveMentees] = useState<{ mentorship_id: string; mentee_user_id: string; goals?: string | null; request_message?: string | null; started_at?: string | null }[]>([])
  const [myProfile, setMyProfile] = useState<Mentor | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [mode, setMode] = useState('')
  const [selected, setSelected] = useState<Mentor | null>(null)
  const [meetingTarget, setMeetingTarget] = useState<{ memberId: string; name: string } | null>(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const mentorEligible = ['professional', 'academician'].includes(user.role)
  const base = '/mentorship/mentors'

  async function load() {
    setLoading(true); setError('')
    const [mentorResult, sentResult, receivedResult, activeMentorResult, activeMenteeResult, profileResult] = await Promise.all([
      request<Mentor[]>(`${base}/discover?limit=100&offset=0&accepting_only=true`, token).catch(() => []),
      request<{ mentorships: Mentorship[] }>(`${base}/requests/sent?limit=100&offset=0`, token).catch(() => ({ mentorships: [] })),
      mentorEligible ? request<{ mentorships: Mentorship[] }>(`${base}/requests/received?pending_only=true&limit=100&offset=0`, token).catch(() => ({ mentorships: [] })) : Promise.resolve({ mentorships: [] }),
      request<{ mentorship_id: string; mentor: Mentor; goals?: string | null; started_at?: string | null }[]>(`${base}/my-mentors`, token).catch(() => []),
      mentorEligible ? request<{ mentorship_id: string; mentee_user_id: string; goals?: string | null; request_message?: string | null; started_at?: string | null }[]>(`${base}/my-mentees`, token).catch(() => []) : Promise.resolve([]),
      mentorEligible ? request<Mentor>(`${base}/me`, token).catch(() => null) : Promise.resolve(null),
    ])
    setMentors(mentorResult); setSent(sentResult.mentorships); setReceived(receivedResult.mentorships); setActiveMentors(activeMentorResult); setActiveMentees(activeMenteeResult); setMyProfile(profileResult)
    setLoading(false)
  }
  useEffect(() => { void load() }, [token, user.role])

  const labelName = (id: string) => members.find((member) => member.id === id)?.full_name || 'CollabVerse member'
  const format = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
  const filteredMentors = mentors.filter((mentor) => {
    const name = labelName(mentor.user_id).toLowerCase()
    const query = search.toLowerCase().trim()
    return (!query || `${name} ${mentor.headline || ''} ${mentor.designation || ''} ${(mentor.mentor_domains || []).join(' ')} ${(mentor.mentoring_topics || []).join(' ')}`.toLowerCase().includes(query)) && (!mode || mentor.mentoring_mode === mode)
  })
  const findMentor = (id: string) => mentors.find((mentor) => mentor.id === id)

  async function requestMentor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected) return
    const form = new FormData(event.currentTarget); setBusy(selected.id); setError(''); setNotice('')
    try {
      await request(`${base}/requests`, token, { method: 'POST', body: JSON.stringify({ mentor_profile_id: selected.id, request_message: String(form.get('request_message') || '').trim() || null, goals: String(form.get('goals') || '').trim() || null }) })
      setSelected(null); setNotice(`Your mentorship request was sent to ${labelName(selected.user_id)}.`); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not send this mentorship request.') }
    finally { setBusy('') }
  }

  async function respondToRequest(item: Mentorship, action: 'accept' | 'reject') {
    setBusy(item.id); setError(''); setNotice('')
    try {
      await request(`${base}/requests/${item.id}/${action}`, token, { method: 'POST', body: JSON.stringify({}) })
      setNotice(action === 'accept' ? 'Mentorship accepted. You can now connect through Messages.' : 'Request declined.'); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : `Could not ${action} this request.`) }
    finally { setBusy('') }
  }

  async function endMentorship(id: string, action: 'complete' | 'cancel') {
    setBusy(id); setError(''); setNotice('')
    try {
      await request(`${base}/requests/${id}/${action}`, token, { method: 'POST', body: JSON.stringify(action === 'complete' ? {} : { cancellation_reason: 'Ended by participant' }) })
      setNotice(action === 'complete' ? 'Mentorship marked as completed.' : 'Mentorship ended.'); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : `Could not ${action} this mentorship.`) }
    finally { setBusy('') }
  }

  async function saveMentorProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy('profile'); setError(''); setNotice('')
    const form = new FormData(event.currentTarget)
    const list = (key: string) => String(form.get(key) || '').split(',').map((item) => item.trim()).filter(Boolean)
    const payload = { headline: String(form.get('headline') || '').trim() || null, designation: String(form.get('designation') || '').trim() || null, bio: String(form.get('bio') || '').trim() || null, years_of_experience: Number(form.get('years_of_experience') || 0), mentor_domains: list('mentor_domains'), mentoring_topics: list('mentoring_topics'), mentoring_mode: String(form.get('mentoring_mode') || 'online'), is_accepting_mentees: true, max_mentees: Number(form.get('max_mentees') || 3) }
    try {
      const profile = await request<Mentor>(`${base}${myProfile ? '/me' : ''}`, token, { method: myProfile ? 'PATCH' : 'POST', body: JSON.stringify(payload) })
      setMyProfile(profile); setNotice(myProfile ? 'Your mentor profile has been updated.' : 'Your mentor profile is live. Mentees can now find you.'); await load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save your mentor profile.') }
    finally { setBusy('') }
  }

  async function proposeMeeting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!meetingTarget) return
    const form = new FormData(event.currentTarget)
    const localTime = String(form.get('meeting_time') || '')
    if (!localTime) return
    setBusy('meeting'); setError(''); setNotice('')
    try {
      const conversation = await request<Conversation>('/messaging/conversations/direct', token, { method: 'POST', body: JSON.stringify({ recipient_user_id: meetingTarget.memberId }) })
      const formattedTime = new Date(localTime).toLocaleString([], { dateStyle: 'full', timeStyle: 'short' })
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
      const agenda = String(form.get('meeting_agenda') || '').trim()
      const content = `Meeting proposal\nProposed time: ${formattedTime} (${timezone})${agenda ? `\nAgenda: ${agenda}` : ''}\nPlease confirm or suggest another time.`
      await request<Message>(`/messaging/conversations/${conversation.id}/messages`, token, { method: 'POST', body: JSON.stringify({ content }) })
      const memberId = meetingTarget.memberId
      setMeetingTarget(null)
      onMessage(memberId)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not send this meeting proposal.') }
    finally { setBusy('') }
  }

  return <section className="mentorship-page">
    <div className="mentorship-hero"><div className="mentorship-hero-copy"><span className="eyebrow">GROW THROUGH SHARED EXPERIENCE</span><h2>Guidance makes the next step clearer.</h2><p>Find someone who’s been there, or share what you’ve learned with the next generation.</p></div><div className="mentorship-orbit"><span>✳</span><i /><i /><i /></div></div>
    {error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}{notice && <div className="project-notice">{notice}<button onClick={() => setNotice('')}>×</button></div>}
    {mentorEligible && <section className="mentor-profile-strip card"><span className="mentor-profile-icon"><Icon name="profile" size={18} /></span><span><strong>{myProfile ? 'Your mentor profile' : 'Share your experience'}</strong><small>{myProfile ? `${myProfile.mentor_domains?.length || 0} focus areas · ${myProfile.is_accepting_mentees ? 'Accepting mentees' : 'Not accepting'}` : 'Create a mentor profile so learners can find and request your guidance.'}</small></span><button onClick={() => setTab('my requests')}>{myProfile ? 'Manage requests' : 'Become a mentor'} <span>→</span></button></section>}
    {mentorEligible && tab === 'my requests' && <form className="mentor-profile-form card" onSubmit={(event) => void saveMentorProfile(event)}><div className="project-form-heading"><div><span className="eyebrow">MENTOR PROFILE</span><h2>{myProfile ? 'Update your profile' : 'Set up your mentor profile'}</h2></div></div><div className="mentor-form-grid"><label className="project-field">Headline<input name="headline" defaultValue={myProfile?.headline || ''} placeholder="e.g. Product leader helping early-career designers" /></label><label className="project-field">Designation<input name="designation" defaultValue={myProfile?.designation || ''} placeholder="Your current role" /></label><label className="project-field">Years of experience<input name="years_of_experience" type="number" min="0" max="80" defaultValue={myProfile?.years_of_experience ?? 0} /></label><label className="project-field">Mentoring format<select name="mentoring_mode" defaultValue={myProfile?.mentoring_mode || 'online'}><option value="online">Online</option><option value="hybrid">Hybrid</option><option value="offline">In person</option></select></label><label className="project-field">Focus areas<input name="mentor_domains" defaultValue={myProfile?.mentor_domains?.join(', ') || ''} placeholder="Research, product, leadership" /></label><label className="project-field">Topics you can help with<input name="mentoring_topics" defaultValue={myProfile?.mentoring_topics?.join(', ') || ''} placeholder="Career planning, interviews" /></label><label className="project-field">Mentee capacity<input name="max_mentees" type="number" min="1" max="100" defaultValue={myProfile?.max_mentees || 3} /></label></div><label className="project-field mentor-bio-field">About your mentoring<textarea name="bio" rows={3} defaultValue={myProfile?.bio || ''} placeholder="How do you like to support people? What can a mentee expect?" /></label><div className="project-form-footer"><span>Separate focus areas and topics with commas.</span><button className="primary-button" disabled={busy === 'profile'}>{busy === 'profile' ? 'Saving…' : myProfile ? 'Save changes' : 'Publish mentor profile'} <span>↗</span></button></div></form>}
    <div className="mentorship-controls"><div className="mentorship-tabs"><button className={tab === 'discover' ? 'mentorship-tab-active' : ''} onClick={() => setTab('discover')}>Find a mentor</button><button className={tab === 'my requests' ? 'mentorship-tab-active' : ''} onClick={() => setTab('my requests')}>Requests <span>{sent.filter((item) => item.status === 'pending').length + received.length || ''}</span></button><button className={tab === 'active' ? 'mentorship-tab-active' : ''} onClick={() => setTab('active')}>Active mentoring <span>{activeMentors.length + activeMentees.length || ''}</span></button></div>{tab === 'discover' && <div className="mentor-filters"><label><Icon name="search" size={14} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name or expertise" /></label><select aria-label="Mentoring format" value={mode} onChange={(event) => setMode(event.target.value)}><option value="">Any format</option><option value="online">Online</option><option value="hybrid">Hybrid</option><option value="offline">In person</option></select></div>}</div>
    {tab === 'discover' ? <><div className="mentorship-section-heading"><div><h2>Mentors accepting requests</h2><p>Find practical guidance from professionals and academics.</p></div><span>{filteredMentors.length} available</span></div>{loading ? <div className="projects-loading card"><span className="loading-spinner" /><p>Finding mentors…</p></div> : filteredMentors.length ? <div className="mentor-grid">{filteredMentors.map((mentor) => { const existing = sent.find((item) => item.mentor_profile_id === mentor.id && ['pending', 'accepted'].includes(item.status)); return <article className="mentor-card card" key={mentor.id}><div className="mentor-card-cover"><span className="mentor-badge">{mentor.is_verified ? '✓ Verified mentor' : 'Mentor'}</span><span className="mentor-mode">{format(mentor.mentoring_mode)}</span><Avatar name={labelName(mentor.user_id)} large /></div><div className="mentor-card-body"><h3>{labelName(mentor.user_id)}</h3><strong className="mentor-designation">{mentor.designation || mentor.headline || 'Experienced professional'}</strong><p className="mentor-headline">{mentor.headline || mentor.bio || 'Sharing experience and guidance with the community.'}</p><div className="mentor-experience">{mentor.years_of_experience != null ? `${mentor.years_of_experience} years of experience` : 'Experienced mentor'}{mentor.max_mentees ? ` · Capacity ${mentor.max_mentees}` : ''}</div>{mentor.mentor_domains?.length > 0 && <div className="mentor-tags">{mentor.mentor_domains.slice(0, 3).map((item) => <span key={item}>{item}</span>)}</div>}<div className="mentor-card-footer"><span><small>MENTORING TOPICS</small><strong>{mentor.mentoring_topics?.slice(0, 2).join(' · ') || mentor.mentor_domains?.slice(0, 2).join(' · ') || 'Career development'}</strong></span>{existing ? <button className="mentor-requested" disabled>{existing.status === 'accepted' ? 'Active' : 'Requested'}</button> : <button className="primary-button" onClick={() => setSelected(mentor)}>Request mentorship <span>↗</span></button>}</div></div></article>})}</div> : <div className="projects-empty card"><span className="message-empty-icon"><Icon name="mentorship" size={22} /></span><h3>{search || mode ? 'No mentors match those filters' : 'More mentors are joining soon'}</h3><p>{search || mode ? 'Try another name, expertise area, or mentoring format.' : 'When mentors publish their profiles, you’ll be able to explore and send a request here.'}</p></div>}</> : tab === 'my requests' ? <div className="mentorship-requests-section"><div className="mentorship-section-heading"><div><h2>Requests you’ve sent</h2><p>Track the status of your mentorship requests.</p></div><span>{sent.length} total</span></div>{loading ? <div className="projects-loading card"><span className="loading-spinner" /><p>Loading your requests…</p></div> : sent.length ? <div className="mentorship-request-list">{sent.map((item) => { const mentor = findMentor(item.mentor_profile_id); return <article className="mentorship-request-card card" key={item.id}><Avatar name={mentor ? labelName(mentor.user_id) : 'Mentor'} /><div className="mentorship-request-copy"><strong>{mentor ? labelName(mentor.user_id) : 'Mentorship request'}</strong><small>{mentor?.designation || mentor?.headline || 'Mentor'} · Requested {timeAgo(item.requested_at)}</small>{item.request_message && <p>{item.request_message}</p>}</div><span className={`mentorship-status mentorship-${item.status}`}>{format(item.status)}</span>{item.status === 'pending' && <button className="project-view-button" disabled={busy === item.id} onClick={() => void endMentorship(item.id, 'cancel')}>Cancel request</button>}</article>})}</div> : <div className="projects-empty card"><span className="message-empty-icon"><Icon name="mentorship" size={22} /></span><h3>No mentorship requests yet</h3><p>Find a mentor whose experience aligns with your goals and send a thoughtful request.</p><button className="primary-button" onClick={() => setTab('discover')}>Explore mentors</button></div>}
      {mentorEligible && <><div className="mentorship-section-heading received-heading"><div><h2>Requests to you</h2><p>Review learners who are looking for your guidance.</p></div><span>{received.length} pending</span></div>{!loading && received.length > 0 && <div className="mentorship-request-list">{received.map((item) => <article className="mentorship-request-card card" key={item.id}><Avatar name={labelName(item.mentee_user_id)} /><div className="mentorship-request-copy"><strong>{labelName(item.mentee_user_id)}</strong><small>Requested {timeAgo(item.requested_at)}</small>{item.goals && <p><b>Goals:</b> {item.goals}</p>}{item.request_message && <p>{item.request_message}</p>}</div><div className="request-decision"><button className="primary-button" disabled={busy === item.id} onClick={() => void respondToRequest(item, 'accept')}>Accept</button><button className="decline-request" disabled={busy === item.id} onClick={() => void respondToRequest(item, 'reject')}>Decline</button></div></article>)}</div>}</>}
      </div> : <div className="mentorship-requests-section"><div className="mentorship-section-heading"><div><h2>Active mentorships</h2><p>Keep your ongoing mentoring relationships moving forward.</p></div><span>{activeMentors.length + activeMentees.length} active</span></div>{loading ? <div className="projects-loading card"><span className="loading-spinner" /><p>Loading active mentorships…</p></div> : activeMentors.length + activeMentees.length ? <div className="active-mentorship-list">{activeMentors.map((item) => <article className="active-mentorship-card card" key={item.mentorship_id}><span className="active-mark">✳</span><div><small>YOUR MENTOR</small><h3>{labelName(item.mentor.user_id)}</h3><p>{item.mentor.designation || item.mentor.headline || 'Mentor'}{item.goals ? ` · ${item.goals}` : ''}</p></div><div className="mentorship-active-actions"><button type="button" className="mentorship-chat-button" onClick={() => onMessage(item.mentor.user_id)}>Message</button><button type="button" className="mentorship-meeting-button" onClick={() => setMeetingTarget({ memberId: item.mentor.user_id, name: labelName(item.mentor.user_id) })}>Schedule meeting</button></div><button className="active-complete" disabled={busy === item.mentorship_id} onClick={() => void endMentorship(item.mentorship_id, 'complete')}>Mark complete</button><button className="active-cancel" disabled={busy === item.mentorship_id} onClick={() => void endMentorship(item.mentorship_id, 'cancel')}>End</button></article>)}{activeMentees.map((item) => <article className="active-mentorship-card card" key={item.mentorship_id}><span className="active-mark">✳</span><div><small>YOUR MENTEE</small><h3>{labelName(item.mentee_user_id)}</h3><p>{item.goals || item.request_message || 'Active mentorship'}</p></div><div className="mentorship-active-actions"><button type="button" className="mentorship-chat-button" onClick={() => onMessage(item.mentee_user_id)}>Message</button><button type="button" className="mentorship-meeting-button" onClick={() => setMeetingTarget({ memberId: item.mentee_user_id, name: labelName(item.mentee_user_id) })}>Schedule meeting</button></div><button className="active-complete" disabled={busy === item.mentorship_id} onClick={() => void endMentorship(item.mentorship_id, 'complete')}>Mark complete</button><button className="active-cancel" disabled={busy === item.mentorship_id} onClick={() => void endMentorship(item.mentorship_id, 'cancel')}>End</button></article>)}</div> : <div className="projects-empty card"><span className="message-empty-icon"><Icon name="mentorship" size={22} /></span><h3>No active mentorships yet</h3><p>Accepted requests will appear here so both mentor and mentee can track their progress.</p></div>}</div>}
    {meetingTarget && <div className="mentor-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setMeetingTarget(null) }}><form className="mentor-request-modal meeting-proposal-modal card" onSubmit={(event) => void proposeMeeting(event)}><button type="button" className="project-close mentor-modal-close" onClick={() => setMeetingTarget(null)} aria-label="Close">×</button><span className="eyebrow">MEETING REQUEST</span><h2>Schedule with {meetingTarget.name}</h2><p>Choose a time and send a meeting proposal in your mentorship chat. Your mentor can confirm or suggest another time.</p><label className="project-field">Date and time<input type="datetime-local" name="meeting_time" min={new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16)} required /></label><label className="project-field">What would you like to discuss?<textarea name="meeting_agenda" rows={3} maxLength={1000} placeholder="Add a topic or short agenda (optional)" /></label><div className="project-form-footer"><span>Shown in your local time zone.</span><button className="primary-button" disabled={busy === 'meeting'}>{busy === 'meeting' ? 'Sending proposal…' : 'Send meeting proposal'} <span>↗</span></button></div></form></div>}
    {selected && <div className="mentor-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelected(null) }}><form className="mentor-request-modal card" onSubmit={(event) => void requestMentor(event)}><button type="button" className="project-close mentor-modal-close" onClick={() => setSelected(null)} aria-label="Close">×</button><span className="eyebrow">MENTORSHIP REQUEST</span><h2>Connect with {labelName(selected.user_id)}</h2><p>Share a little context so they can understand what kind of guidance you’re looking for.</p><label className="project-field">What would you like help with?<textarea name="goals" rows={3} maxLength={5000} placeholder="Describe the skills, decisions, or goals you’d like to work on." /></label><label className="project-field">Message to the mentor<textarea name="request_message" rows={3} maxLength={3000} placeholder="Introduce yourself and explain why their experience stood out." /></label><div className="project-form-footer"><span>Keep it specific and respectful.</span><button className="primary-button" disabled={busy === selected.id}>{busy === selected.id ? 'Sending…' : 'Send request'} <span>↗</span></button></div></form></div>}
  </section>
}

function OpportunitiesComingSoon({ onNavigate }: { onNavigate: (destination: string) => void }) {
  const categories = [
    { icon: 'opportunities', title: 'Jobs', description: 'Explore professional roles from organizations looking for your skills.', tone: 'jobs' },
    { icon: 'projects', title: 'Internships', description: 'Find hands-on experience, mentorship, and a strong start to your career.', tone: 'internships' },
    { icon: 'mentorship', title: 'Opportunities', description: 'Discover research, fellowships, grants, and other ways to grow.', tone: 'other' },
  ]
  return <section className="opportunities-coming-page"><div className="opportunities-coming-hero"><div className="coming-orbit"><span>✳</span><i /><i /><i /></div><span className="coming-kicker"><span className="coming-live-dot" /> THE NEXT CHAPTER</span><h2>New opportunities are on the way.</h2><p>We’re building a thoughtful space to connect people with the right next step in their professional journey.</p><span className="coming-soon-pill">COMING SOON</span><div className="coming-progress"><span /></div><small className="coming-progress-caption">We’re getting things ready</small></div><div className="coming-categories">{categories.map((category) => <article className="coming-category card" key={category.title}><span className={`coming-category-icon coming-${category.tone}`}><Icon name={category.icon} size={19} /></span><div><h3>{category.title}</h3><p>{category.description}</p></div><span className="coming-category-status">Coming soon</span></article>)}</div><div className="coming-footer"><div><span className="eyebrow">WHILE YOU WAIT</span><strong>Keep building your network and experience.</strong></div><div><button onClick={() => onNavigate('My network')}>Explore your network <span>→</span></button><button onClick={() => onNavigate('Projects')}>Browse projects <span>→</span></button></div></div></section>
}

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true as const }
  if (name === 'home') return <svg {...common}><path d="m3.5 10 8.5-7 8.5 7"/><path d="M5.5 9v11h13V9M9.5 20v-6h5v6"/></svg>
  if (name === 'network') return <svg {...common}><circle cx="9" cy="8" r="3.2"/><path d="M3 20c.3-3.3 2.2-5.2 6-5.2s5.7 1.9 6 5.2"/><path d="M16 5.2a3.1 3.1 0 0 1 0 5.8M17 14.8c2.4.4 3.7 2.1 4 5.2"/></svg>
  if (name === 'opportunities') return <svg {...common}><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5.5A1.5 1.5 0 0 1 9.5 4h5A1.5 1.5 0 0 1 16 5.5V7M3 12h18M10 12v2h4v-2"/></svg>
  if (name === 'projects') return <svg {...common}><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></svg>
  if (name === 'mentorship') return <svg {...common}><path d="m12 3 2.4 5 5.6.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.6-.8L12 3Z"/><path d="M7 20h10"/></svg>
  if (name === 'messages') return <svg {...common}><path d="M20.5 11.5a7.8 7.8 0 0 1-8.5 7.5 9.5 9.5 0 0 1-4-.8L3 20l1.4-4.1A7.1 7.1 0 0 1 3.5 12c0-4.2 3.8-7.5 8.5-7.5s8.5 3.1 8.5 7Z"/><path d="M8 12h.01M12 12h.01M16 12h.01"/></svg>
  if (name === 'bell') return <svg {...common}><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4"/></svg>
  if (name === 'search') return <svg {...common}><circle cx="10.8" cy="10.8" r="6.6"/><path d="m16 16 4.5 4.5"/></svg>
  if (name === 'image') return <svg {...common}><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/></svg>
  if (name === 'profile') return <svg {...common}><circle cx="12" cy="8" r="3.2"/><path d="M5 20c.5-3.6 2.8-5.5 7-5.5s6.5 1.9 7 5.5"/></svg>
  if (name === 'bookmark') return <svg {...common}><path d="M6 4.8A1.8 1.8 0 0 1 7.8 3h8.4A1.8 1.8 0 0 1 18 4.8V21l-6-4-6 4V4.8Z"/></svg>
  if (name === 'news') return <svg {...common}><path d="M5 4h14a2 2 0 0 1 2 2v13H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 8h10M7 12h4M7 16h10m3-4h-2v4h2"/></svg>
  if (name === 'ai') return <svg {...common}><path d="M12 3v3M12 18v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1m0-12.8-2.1 2.1m-8.6 8.6-2.1 2.1"/><circle cx="12" cy="12" r="5"/><path d="m10.5 12 1 1 2-2"/></svg>
  if (name === 'courses') return <svg {...common}><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21V5.5Z"/><path d="M4 17a2.5 2.5 0 0 1 2.5-2.5H20M8 7h8m-8 3h6"/></svg>
  if (name === 'assessment') return <svg {...common}><rect x="4" y="3.5" width="16" height="17" rx="2"/><path d="M8 8h8m-8 4h2m4 0h2m-8 4h2m4 0h2"/></svg>
  if (name === 'chevron') return <svg {...common}><path d="m7 10 5 5 5-5"/></svg>
  return <svg {...common}><circle cx="12" cy="12" r="8"/></svg>
}

function Avatar({ name, large = false, imageUrl }: { name: string; large?: boolean; imageUrl?: string | null }) { return <div className={`avatar ${large ? 'avatar-large' : ''}`} aria-label={name}>{initials(name)}{imageUrl && <img src={imageUrl} alt="" onError={(event) => { event.currentTarget.style.display = 'none' }} />}</div> }

function PostCard({ post, currentUser, token, members, onLike, onCommentPosted, onOpenProfile, saved, onToggleSave, onDelete }: { post: Post; currentUser: User; token: string; members: PublicUser[]; onLike: () => void; onCommentPosted: () => void; onOpenProfile: (memberId: string) => void; saved: boolean; onToggleSave: () => Promise<boolean>; onDelete: () => void }) {
  const ownPost = post.author_id === currentUser.id
  const [activeMediaIndex, setActiveMediaIndex] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const [reportReason, setReportReason] = useState('spam')
  const [reportDetails, setReportDetails] = useState('')
  const [reporting, setReporting] = useState(false)
  const [menuMessage, setMenuMessage] = useState('')
  const [commenting, setCommenting] = useState(false)
  const [comments, setComments] = useState<PostComment[]>([])
  const [commentsLoading, setCommentsLoading] = useState(false)
  const [commentDraft, setCommentDraft] = useState('')
  const [commentError, setCommentError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const author = members.find((member) => member.id === post.author_id)
  const authorName = ownPost ? currentUser.profile?.full_name || currentUser.email.split('@')[0] : author?.full_name || 'CollabVerse member'
  const authorHeadline = ownPost ? String(currentUser.profile?.headline || currentUser.profile?.designation || roleName(currentUser.role)) : author?.headline || roleName(author?.role)
  const peopleById = new Map(members.map((member) => [member.id, member]))
  const commentName = (userId: string) => userId === currentUser.id ? currentUser.profile?.full_name || currentUser.email.split('@')[0] : peopleById.get(userId)?.full_name || 'CollabVerse member'

  useEffect(() => {
    if (!commenting) return
    setCommentsLoading(true); setCommentError('')
    void request<PostComment[]>(`/posts/${post.id}/comments`, token).then(setComments).catch((reason) => setCommentError(reason instanceof Error ? reason.message : 'Could not load comments.')).finally(() => setCommentsLoading(false))
  }, [commenting, post.id, token])

  async function submitComment(event: FormEvent) {
    event.preventDefault(); if (!commentDraft.trim()) return
    setSubmitting(true); setCommentError('')
    try {
      const created = await request<PostComment>(`/posts/${post.id}/comments`, token, { method: 'POST', body: JSON.stringify({ content: commentDraft.trim() }) })
      setComments((current) => [...current, created]); setCommentDraft(''); onCommentPosted()
    } catch (reason) { setCommentError(reason instanceof Error ? reason.message : 'Could not send your comment.') }
    finally { setSubmitting(false) }
  }

  const permalink = `${window.location.origin}/#post-${post.id}`
  async function sharePost() {
    if (navigator.share) {
      try { await navigator.share({ title: 'CollabVerse post', text: post.content || 'A post on CollabVerse', url: permalink }) } catch { /* Share sheet dismissed. */ }
    } else {
      try { await navigator.clipboard?.writeText(permalink) } catch { setCommentError('Could not copy the post link.') }
    }
  }

  async function submitReport(event: FormEvent) {
    event.preventDefault(); setReporting(true); setMenuMessage('')
    try {
      await request(`/posts/${post.id}/report`, token, { method: 'POST', body: JSON.stringify({ reason: reportReason, details: reportDetails.trim() || null }) })
      setReportOpen(false); setReportDetails(''); setMenuMessage('Report submitted for review.')
    } catch (reason) { setMenuMessage(reason instanceof Error ? reason.message : 'Could not submit the report.') }
    finally { setReporting(false) }
  }

  return <article id={`post-${post.id}`} className="post-card card"><div className="post-top"><button className="post-avatar-link" onClick={() => !ownPost && onOpenProfile(post.author_id)} aria-label={`View ${authorName}'s profile`}><Avatar name={authorName} imageUrl={ownPost ? currentUser.avatar_url : author?.avatar_url} /></button><div className="post-author"><button className="post-author-link" onClick={() => !ownPost && onOpenProfile(post.author_id)}>{authorName}</button><span>{authorHeadline}</span><small>{timeAgo(post.created_at)} <span>·</span> <span className="globe">◎</span></small></div><div className="post-menu-wrap"><button className="more-button" aria-label="More post actions" aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>···</button>{menuOpen && <><button className="post-menu-dismiss" aria-label="Close post menu" onClick={() => setMenuOpen(false)} /><div className="post-menu"><button onClick={() => { setMenuOpen(false); void onToggleSave().catch((reason) => setMenuMessage(reason instanceof Error ? reason.message : 'Could not update saved posts.')) }}><Icon name="bookmark" size={15} />{saved ? 'Remove from saved' : 'Save post'}</button>{ownPost ? <button className="post-menu-danger" onClick={() => { setMenuOpen(false); onDelete() }}>Delete post</button> : <button onClick={() => { setMenuOpen(false); setReportOpen(true) }}>Report post</button>}</div></>}</div></div>{menuMessage && <div className="post-menu-message" role="status">{menuMessage}</div>}{reportOpen && <div className="mentor-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setReportOpen(false) }}><form className="post-report-modal card" onSubmit={submitReport}><button type="button" className="mentor-modal-close" aria-label="Close" onClick={() => setReportOpen(false)}>×</button><span className="eyebrow">COMMUNITY SAFETY</span><h2>Report this post</h2><p>Tell us what’s wrong. Reports are sent to the moderation team for review.</p><label className="project-field">Reason<select value={reportReason} onChange={(event) => setReportReason(event.target.value)}><option value="spam">Spam</option><option value="harassment">Harassment</option><option value="hate">Hate or discrimination</option><option value="false_information">False information</option><option value="inappropriate">Inappropriate content</option><option value="other">Other</option></select></label><label className="project-field">Additional details<textarea value={reportDetails} onChange={(event) => setReportDetails(event.target.value)} maxLength={1000} rows={4} placeholder="Share any helpful context (optional)" /></label>{menuMessage && <div className="comment-error">{menuMessage}</div>}<div className="project-form-footer"><button type="button" className="decline-request" onClick={() => setReportOpen(false)}>Cancel</button><button className="primary-button" disabled={reporting}>{reporting ? 'Submitting…' : 'Submit report'}</button></div></form></div>}{post.content && <p className="post-content">{post.content}</p>}{Boolean(post.media?.length) && <div className="post-media-carousel"><div className="post-media-track" style={{ width: `${post.media!.length * 100}%`, transform: `translateX(-${activeMediaIndex * (100 / post.media!.length)}%)` }}>{post.media!.map((media, index) => <div className="post-media-slide" key={media.id} style={{ flex: `0 0 ${100 / post.media!.length}%` }}>{media.media_type === 'image' ? <img className="post-media" src={media.media_url} alt={`Photo ${index + 1} of ${post.media!.length} shared by ${authorName}`} loading="lazy" /> : <video className="post-media" src={media.media_url} poster={media.thumbnail_url || undefined} controls preload="metadata" />}</div>)}</div>{post.media!.length > 1 && <><button className="post-carousel-arrow post-carousel-prev" aria-label="Previous photo" disabled={activeMediaIndex === 0} onClick={() => setActiveMediaIndex((index) => Math.max(0, index - 1))}>‹</button><button className="post-carousel-arrow post-carousel-next" aria-label="Next photo" disabled={activeMediaIndex === post.media!.length - 1} onClick={() => setActiveMediaIndex((index) => Math.min(post.media!.length - 1, index + 1))}>›</button><span className="post-carousel-count">{activeMediaIndex + 1} / {post.media!.length}</span></>}</div>}{post.post_type === 'project' && <div className="project-attachment"><span className="attachment-icon">▧</span><span><small>PROJECT UPDATE</small><strong>View shared project</strong></span><span className="arrow">↗</span></div>}<div className="post-metrics"><span>{post.like_count ? `${post.like_count} ${post.like_count === 1 ? 'appreciation' : 'appreciations'}` : 'Be the first to appreciate this'}</span><button onClick={() => setCommenting((value) => !value)}>{post.comment_count} {post.comment_count === 1 ? 'comment' : 'comments'}</button></div><div className="post-actions"><button className={post.liked_by_me ? 'liked' : ''} onClick={onLike}><span>{post.liked_by_me ? '♥' : '♡'}</span> Appreciate</button><button onClick={() => setCommenting((value) => !value)}><span>▱</span> Comment</button><button onClick={() => void sharePost()}><span>↗</span> Share</button></div>{commenting && <div className="comments-panel"><div className="comments-heading"><strong>Conversation</strong><span>{comments.length} {comments.length === 1 ? 'comment' : 'comments'}</span></div>{commentsLoading ? <div className="comment-loading">Loading comments…</div> : comments.length > 0 ? <div className="comment-list">{comments.map((comment) => { const name = commentName(comment.user_id); return <div className="comment-row" key={comment.id}><Avatar name={name} imageUrl={comment.user_id === currentUser.id ? currentUser.avatar_url : peopleById.get(comment.user_id)?.avatar_url} /><div className="comment-bubble"><div><strong>{name}</strong><small>{timeAgo(comment.created_at)}</small></div><p>{comment.content}</p></div></div> })}</div> : <div className="comment-loading">Start the conversation with a thoughtful comment.</div>}{commentError && <div className="comment-error">{commentError}</div>}<form className="comment-form" onSubmit={submitComment}><Avatar name={currentUser.profile?.full_name || currentUser.email} imageUrl={currentUser.avatar_url} /><input value={commentDraft} onChange={(event) => setCommentDraft(event.target.value)} placeholder="Write a comment…" maxLength={2000} /><button disabled={!commentDraft.trim() || submitting}>{submitting ? 'Sending…' : 'Comment'}</button></form></div>}</article>
}

function SavedPostsScreen({ token, user, members, savedPostIds, onToggleSave, onDeletePost, onOpenProfile }: { token: string; user: User; members: PublicUser[]; savedPostIds: string[]; onToggleSave: (postId: string) => Promise<boolean>; onDeletePost: (post: Post) => Promise<boolean>; onOpenProfile: (memberId: string) => void }) {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    void request<Post[]>('/posts/saved?limit=100&offset=0', token).then((items) => { if (active) setPosts(items) }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Could not load saved posts.') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token])
  async function toggleLike(post: Post) {
    try { const result = await request<{ liked: boolean; like_count: number }>(`/posts/${post.id}/like`, token, { method: 'POST' }); setPosts((items) => items.map((item) => item.id === post.id ? { ...item, liked_by_me: result.liked, like_count: result.like_count } : item)) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update appreciation.') }
  }
  return <section className="saved-posts-page"><div className="saved-posts-intro card"><span className="saved-posts-icon"><Icon name="bookmark" size={20} /></span><div><h2>Your saved posts</h2><p>Keep useful ideas and updates close at hand.</p></div><span className="saved-posts-count">{savedPostIds.length} saved</span></div>{error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}{loading ? <div className="empty-state card"><div className="comment-loading">Loading saved posts…</div></div> : posts.length ? <div className="post-list">{posts.map((post) => <PostCard key={post.id} post={post} currentUser={user} token={token} members={members} onOpenProfile={onOpenProfile} saved={savedPostIds.includes(post.id)} onToggleSave={async () => { const isSaved = await onToggleSave(post.id); if (!isSaved) setPosts((items) => items.filter((item) => item.id !== post.id)); return isSaved }} onDelete={async () => { if (await onDeletePost(post)) setPosts((items) => items.filter((item) => item.id !== post.id)) }} onLike={() => void toggleLike(post)} onCommentPosted={() => setPosts((items) => items.map((item) => item.id === post.id ? { ...item, comment_count: item.comment_count + 1 } : item))} />)}</div> : <div className="empty-state card"><div className="empty-illustration"><Icon name="bookmark" size={23} /></div><h2>No saved posts yet</h2><p>Use the three-dot menu on any post to save it here for later.</p></div>}</section>
}

function NetworkScreen({ token, currentUserId, setError, onOpenProfile, onMessage }: { token: string; currentUserId: string; setError: (message: string) => void; onOpenProfile: (memberId: string) => void; onMessage: (memberId: string) => void }) {
  const [people, setPeople] = useState<PublicUser[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [incoming, setIncoming] = useState<Connection[]>([])
  const [outgoing, setOutgoing] = useState<Connection[]>([])
  const [view, setView] = useState<'discover' | 'connections' | 'invitations'>('discover')
  const [query, setQuery] = useState('')
  const [busyId, setBusyId] = useState('')
  const [loading, setLoading] = useState(true)

  async function refresh() {
    setLoading(true)
    try {
      const [directory, accepted, received, sent] = await Promise.all([
        request<PublicUser[]>('/users/directory?limit=100', token),
        request<Connection[]>('/connections', token),
        request<Connection[]>('/connections/requests/incoming', token),
        request<Connection[]>('/connections/requests/outgoing', token),
      ])
      const bots = new Set(directory.filter(isTestAccount).map((person) => person.id))
      setPeople(directory.filter((person) => !bots.has(person.id)))
      setConnections(accepted.filter((item) => !bots.has(item.requester_id) && !bots.has(item.recipient_id)))
      setIncoming(received.filter((item) => !bots.has(item.requester_id)))
      setOutgoing(sent.filter((item) => !bots.has(item.recipient_id)))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load your network.') }
    finally { setLoading(false) }
  }

  useEffect(() => { void refresh() }, [token])

  async function act(path: string, method: string, id: string) {
    setBusyId(id); setError('')
    try { await request(path, token, { method }); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update your network.') }
    finally { setBusyId('') }
  }

  const connectedUserIds = new Set(connections.map((item) => item.requester_id === currentUserId ? item.recipient_id : item.requester_id))
  const pendingUserIds = new Set([...incoming.map((item) => item.requester_id), ...outgoing.map((item) => item.recipient_id)])
  const suggestions = people.filter((person) => !connectedUserIds.has(person.id) && !pendingUserIds.has(person.id) && `${person.full_name} ${person.headline || ''} ${person.role}`.toLowerCase().includes(query.toLowerCase()))
  const byId = new Map(people.map((person) => [person.id, person]))
  const member = (id: string) => byId.get(id) || { id, full_name: 'CollabVerse member', role: 'member', headline: 'Professional community member' }

  return <section className="network-page">
    <div className="network-banner"><div><span className="eyebrow">STRONGER TOGETHER</span><h2>Build your professional network</h2><p>Meet people across academia and industry, and make room for new ideas.</p></div><div className="network-banner-art">♧</div></div>
    <div className="network-stats"><div className="network-stat card"><strong>{connections.length}</strong><span>Connections</span></div><div className="network-stat card"><strong>{incoming.length}</strong><span>Invitations to respond</span></div><div className="network-stat card"><strong>{outgoing.length}</strong><span>Invitations sent</span></div></div>
    <div className="network-tabs"><button className={view === 'discover' ? 'network-tab active' : 'network-tab'} onClick={() => setView('discover')}>Discover people</button><button className={view === 'connections' ? 'network-tab active' : 'network-tab'} onClick={() => setView('connections')}>My connections <span>{connections.length}</span></button><button className={view === 'invitations' ? 'network-tab active' : 'network-tab'} onClick={() => setView('invitations')}>Invitations {incoming.length > 0 && <span className="invitation-dot">{incoming.length}</span>}</button></div>
    {view === 'discover' && <label className="network-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search people by name, role, or organization" /></label>}
    {loading ? <div className="network-loading card">Finding your community…</div> : view === 'discover' ? (
      <div className="member-grid">
        {suggestions.map((person) => <MemberCard key={person.id} person={person} onOpenProfile={() => onOpenProfile(person.id)} actionLabel={busyId === person.id ? 'Sending…' : 'Connect'} onAction={() => void act(`/connections/${person.id}`, 'POST', person.id)} disabled={busyId === person.id} />)}
        {suggestions.length === 0 && <div className="empty-state card network-empty"><div className="empty-illustration">♧</div><h2>{query ? 'No matching people' : 'Your community is growing'}</h2><p>{query ? 'Try another name, role, or organization.' : 'New members will appear here as they join CollabVerse.'}</p></div>}
      </div>
    ) : view === 'connections' ? (
      <div className="member-grid">
        {connections.map((connection) => {
          const personId = connection.requester_id === currentUserId ? connection.recipient_id : connection.requester_id
          return <MemberCard key={connection.id} person={member(personId)} onOpenProfile={() => onOpenProfile(personId)} actionLabel="Message" onAction={() => onMessage(personId)} />
        })}
        {connections.length === 0 && <div className="empty-state card network-empty"><div className="empty-illustration">♧</div><h2>Connections will show here</h2><p>Discover people and send an invitation to start building your network.</p><button className="primary-button" onClick={() => setView('discover')}>Find people</button></div>}
      </div>
    ) : (
      <div className="invitation-list">
        {incoming.map((item) => <MemberCard key={item.id} person={member(item.requester_id)} onOpenProfile={() => onOpenProfile(item.requester_id)} actionLabel={busyId === item.id ? 'Accepting…' : 'Accept'} onAction={() => void act(`/connections/${item.id}/accept`, 'PATCH', item.id)} secondaryLabel="Decline" onSecondary={() => void act(`/connections/${item.id}/reject`, 'PATCH', item.id)} disabled={busyId === item.id} />)}
        {outgoing.map((item) => <MemberCard key={item.id} person={member(item.recipient_id)} onOpenProfile={() => onOpenProfile(item.recipient_id)} actionLabel="Invitation sent" disabled />)}
        {incoming.length + outgoing.length === 0 && <div className="empty-state card network-empty"><div className="empty-illustration">✳</div><h2>No pending invitations</h2><p>When someone invites you to connect, you’ll find it here.</p></div>}
      </div>
    )}
  </section>
}

type Hackathon = { id: string; title: string; description: string; domain?: string | null; organizer_name?: string | null; source_name?: string | null; mode: string; difficulty: string; status: string; location?: string | null; min_team_size: number; max_team_size: number; registration_deadline?: string | null; start_date?: string | null; end_date?: string | null; prize_details?: string | null; registration_url?: string | null; source_url?: string | null; banner_url?: string | null; is_featured: boolean }

function HackathonsScreen({ token }: { token: string }) {
  const [items, setItems] = useState<Hackathon[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState('')
  const [syncNotice, setSyncNotice] = useState('')
  const [query, setQuery] = useState('')
  useEffect(() => {
    let live = true
    void request<{ total: number; hackathons: Hackathon[] }>('/hackathons?limit=100&offset=0', token)
      .then((result) => { if (live) setItems(result.hackathons || []) })
      .catch((reason) => { if (live) setError(reason instanceof Error ? reason.message : 'Could not load hackathons.') })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [token])
  async function refreshListings() {
    setSyncing(true)
    setError('')
    setSyncNotice('')
    try {
      const sync = await request<{ fetched: number; created: number; updated: number }>('/hackathons/sync/unstop?max_pages=2&per_page=18', token, { method: 'POST' })
      const result = await request<{ total: number; hackathons: Hackathon[] }>('/hackathons?limit=100&offset=0', token)
      setItems(result.hackathons || [])
      const saved = sync.created + sync.updated
      setSyncNotice(saved ? `Found ${sync.fetched} listings and added or refreshed ${saved}.` : 'No new open hackathons were found. Try again later.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not refresh hackathon listings.')
    } finally {
      setSyncing(false)
    }
  }
  const filtered = items.filter((item) => `${item.title} ${item.description} ${item.domain || ''} ${item.organizer_name || ''}`.toLowerCase().includes(query.trim().toLowerCase()))
  const date = (value?: string | null) => value ? new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : ''
  const label = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
  return <section className="hackathons-page"><div className="hackathons-banner"><span className="hackathons-banner-icon"><Icon name="assessment" size={23} /></span><div className="hackathons-banner-copy"><span className="eyebrow">BUILD, LEARN, COMPETE</span><h2>Find your next hackathon</h2><p>Explore challenges and meet collaborators who are ready to build.</p></div><button className="hackathons-sync-button" onClick={() => void refreshListings()} disabled={syncing}>{syncing ? 'Finding listings…' : 'Refresh listings'}</button></div><label className="hackathons-search"><Icon name="search" size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by challenge, domain, or organizer" /></label>{syncNotice && <p className="hackathons-sync-notice" role="status">{syncNotice}</p>}{error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}{loading ? <div className="projects-loading card"><span className="loading-spinner" /><p>Finding hackathons…</p></div> : filtered.length ? <div className="hackathon-grid">{filtered.map((item) => <article className="hackathon-card card" key={item.id}>{item.banner_url && <img className="hackathon-banner-image" src={item.banner_url} alt="" loading="lazy" />}<div className="hackathon-card-body"><div className="hackathon-card-meta"><span>{item.domain || 'Open challenge'}</span><span className={`project-status status-${item.status}`}>{label(item.status)}</span></div><h3>{item.title}</h3><p>{item.description}</p><div className="hackathon-details"><span>{label(item.mode)}{item.location ? ` · ${item.location}` : ''}</span><span>Team {item.min_team_size}–{item.max_team_size}</span>{item.registration_deadline && <span>Register by {date(item.registration_deadline)}</span>}{item.organizer_name && <span>By {item.organizer_name}</span>}{item.prize_details && <span>{item.prize_details}</span>}</div><footer><small>{item.source_name || 'CollabVerse'}{item.start_date ? ` · ${date(item.start_date)}` : ''}</small>{(item.registration_url || item.source_url) && <a href={item.registration_url || item.source_url || '#'} target="_blank" rel="noreferrer">View challenge <span>↗</span></a>}</footer></div></article>)}</div> : <div className="empty-state card"><div className="empty-illustration"><Icon name="assessment" size={20} /></div><h2>{query ? 'No matching hackathons' : 'No hackathons listed yet'}</h2><p>{query ? 'Try a different challenge, domain, or organizer.' : 'Use “Refresh listings” to look for current challenges from Unstop.'}</p>{!query && <button className="hackathons-empty-refresh" onClick={() => void refreshListings()} disabled={syncing}>{syncing ? 'Finding listings…' : 'Find hackathons'}</button>}</div>}</section>
}

function MemberCard({ person, actionLabel, onAction, onOpenProfile, secondaryLabel, onSecondary, disabled = false }: { person: PublicUser; actionLabel: string; onAction?: () => void; onOpenProfile?: () => void; secondaryLabel?: string; onSecondary?: () => void; disabled?: boolean }) {
  return <article className="member-card card"><div className="member-cover"><span>✳</span></div><button className="member-avatar-link" onClick={onOpenProfile} aria-label={`View ${person.full_name}'s profile`}><Avatar name={person.full_name} large imageUrl={person.avatar_url} /></button><div className="member-info"><h3>{person.full_name}</h3><p>{person.headline || `${roleName(person.role)} · CollabVerse`}</p><span className="role-pill">{roleName(person.role)}</span></div><div className="member-actions"><button className="member-view-profile" onClick={onOpenProfile}>View profile</button>{secondaryLabel && <button className="secondary-button" onClick={onSecondary} disabled={disabled}>{secondaryLabel}</button>}<button className={disabled ? 'connect-button connected-button' : 'connect-button'} onClick={onAction} disabled={disabled}>{actionLabel === 'Message' ? '✉ ' : disabled && !secondaryLabel ? '✓ ' : '+ '}{actionLabel}</button></div></article>
}

type Interest = { id: string; name: string; category: string }
type Goal = { id: string; title: string; description?: string | null; goal_type: string; status: string }
type Learning = { id: string; skill_id: string; skill: { id: string; name: string }; priority: string }
type Skill = { id: string; name: string; category: string }
type PreferenceData = { interests: Interest[]; goals: Goal[]; skills_to_learn: Learning[] }
type ProfileField = { key: string; label: string; kind?: 'textarea' | 'number' | 'url' | 'date'; wide?: boolean; hint?: string }

const profileFields: Record<string, ProfileField[]> = {
  student: [
    { key: 'full_name', label: 'Full name' }, { key: 'institution_name', label: 'Institution' },
    { key: 'course', label: 'Course / degree' }, { key: 'department', label: 'Department' },
    { key: 'graduation_year', label: 'Graduation year', kind: 'number' }, { key: 'career_goal', label: 'Career goal' },
    { key: 'location', label: 'Location' }, { key: 'bio', label: 'About you', kind: 'textarea', wide: true, hint: 'What are you studying, building, or curious about?' },
  ],
  recruiter: [
    { key: 'full_name', label: 'Full name' }, { key: 'designation', label: 'Job title' },
    { key: 'company_name', label: 'Company' }, { key: 'industry', label: 'Industry' },
    { key: 'company_website', label: 'Company website', kind: 'url' },
  ],
  academician: [
    { key: 'full_name', label: 'Full name' }, { key: 'designation', label: 'Title / position' },
    { key: 'institution_name', label: 'Institution' }, { key: 'department', label: 'Department' },
    { key: 'research_interests', label: 'Research areas', kind: 'textarea', wide: true, hint: 'Share your areas of research and expertise.' },
  ],
  professional: [
    { key: 'full_name', label: 'Full name' }, { key: 'headline', label: 'Professional headline', wide: true },
    { key: 'designation', label: 'Job title' }, { key: 'company_name', label: 'Company' },
    { key: 'industry', label: 'Industry' }, { key: 'years_of_experience', label: 'Years of experience', kind: 'number' },
    { key: 'location', label: 'Location' }, { key: 'bio', label: 'About you', kind: 'textarea', wide: true, hint: 'A short introduction about your work and what you care about.' },
    { key: 'linkedin_url', label: 'LinkedIn URL', kind: 'url' }, { key: 'portfolio_url', label: 'Portfolio URL', kind: 'url' }, { key: 'github_url', label: 'GitHub URL', kind: 'url' },
  ],
  institution_admin: [
    { key: 'admin_name', label: 'Your name' }, { key: 'institution_name', label: 'Institution' },
    { key: 'accreditation', label: 'Accreditation' }, { key: 'website', label: 'Website', kind: 'url' },
    { key: 'established_date', label: 'Established date', kind: 'date' },
  ],
}

const interestCategories = [
  ['technology', 'Technology'], ['business', 'Business'], ['finance', 'Finance'], ['marketing', 'Marketing'],
  ['startups', 'Startups'], ['economy', 'Economics'], ['research', 'Research'], ['healthcare', 'Healthcare'],
  ['design', 'Design'], ['law', 'Law'], ['education', 'Education'], ['cybersecurity', 'Cybersecurity'],
  ['data_science', 'Data science'], ['artificial_intelligence', 'Artificial intelligence'],
  ['entrepreneurship', 'Entrepreneurship'], ['operations', 'Operations'], ['global_affairs', 'Global affairs'],
  ['other', 'Other'],
] as const
const interestTopicsByCategory: Record<string, string[]> = {
  technology: ['Software engineering', 'Cloud computing', 'Mobile apps', 'Web development', 'Open source', 'Robotics', 'Game development', 'Blockchain', 'Internet of Things', 'Hardware engineering', 'AR / VR'],
  business: ['Product management', 'Business strategy', 'Consulting', 'Business analysis', 'Customer success', 'Freelancing', 'Remote work', 'Sales', 'Operations management'],
  finance: ['Financial technology', 'Investment analysis', 'Accounting', 'Risk management', 'Personal finance', 'Financial modeling', 'Cryptocurrency'],
  marketing: ['Digital marketing', 'Brand strategy', 'Market research', 'Content strategy', 'Growth marketing', 'SEO', 'Social media', 'Copywriting'],
  startups: ['Startup ecosystems', 'Venture capital', 'Early-stage products', 'Startup operations', 'Founder stories', 'MVP development', 'Pitching'],
  economy: ['Economic policy', 'Development economics', 'Labor markets', 'Behavioral economics', 'Trade', 'Public finance'],
  research: ['Research methods', 'Scientific publishing', 'Interdisciplinary research', 'Research data', 'Innovation', 'Literature reviews', 'Lab research'],
  healthcare: ['Public health', 'Health technology', 'Biomedical research', 'Healthcare access', 'Clinical innovation', 'Mental health', 'Nutrition'],
  design: ['UX research', 'User interface design', 'Accessibility', 'Product design', 'Visual communication', 'Video editing', 'Photo editing', 'Graphic design', 'Motion graphics', 'Animation'],
  law: ['Technology law', 'Intellectual property', 'Public policy', 'Corporate law', 'Human rights', 'Cyber law', 'Legal research'],
  education: ['Learning design', 'Higher education', 'Education technology', 'Teaching practice', 'Student success', 'Online learning', 'Academic writing'],
  cybersecurity: ['Application security', 'Privacy engineering', 'Threat intelligence', 'Digital forensics', 'Network security', 'Ethical hacking', 'Cloud security'],
  data_science: ['Data analytics', 'Machine learning', 'Data visualization', 'Statistics', 'Big data', 'Data engineering', 'Business intelligence'],
  artificial_intelligence: ['Generative AI', 'Responsible AI', 'Natural language processing', 'Computer vision', 'AI in education', 'AI agents', 'Prompt engineering'],
  entrepreneurship: ['Social entrepreneurship', 'Business models', 'Product validation', 'Fundraising', 'Small business', 'Freelancing', 'Creator economy'],
  operations: ['Supply chains', 'Process improvement', 'Project operations', 'Quality management', 'People operations', 'Event planning'],
  global_affairs: ['International development', 'Geopolitics', 'Climate policy', 'Global health', 'International relations', 'Sustainability'],
  other: ['Freelancing', 'Video editing', 'Photo editing', 'Writing and editing', 'Public speaking', 'Photography', 'Music', 'Sports', 'Leadership', 'Community building', 'Volunteering', 'Career development'],
}
const interestDomainsByRole: Record<string, string[]> = {
  student: ['technology', 'research', 'data_science', 'artificial_intelligence', 'business', 'design', 'healthcare', 'education', 'other'],
  academician: ['research', 'education', 'healthcare', 'technology', 'data_science', 'artificial_intelligence', 'law', 'global_affairs', 'other'],
  professional: ['technology', 'business', 'finance', 'marketing', 'design', 'operations', 'artificial_intelligence', 'entrepreneurship', 'other'],
  recruiter: ['technology', 'business', 'finance', 'marketing', 'operations', 'healthcare', 'design', 'startups', 'other'],
  institution_admin: ['education', 'research', 'operations', 'global_affairs', 'finance', 'technology', 'other'],
}
const interestOptions = Object.entries(interestTopicsByCategory).flatMap(([category, topics]) => topics.map((name) => ({ name, category })))
const goalTypes = [['career', 'Career'], ['learning', 'Learning'], ['project', 'Project'], ['internship', 'Internship'], ['research', 'Research'], ['startup', 'Startup'], ['networking', 'Networking'], ['personal', 'Personal']]

function ExploreScreen({ onNavigate, isStudent }: { onNavigate: (destination: string) => void; isStudent: boolean }) {
  const items = [
    { title: 'News', detail: 'Follow research and industry updates matched to your interests.', icon: 'news', action: 'News', tone: 'indigo' },
    { title: 'AI mentor', detail: 'Get help with learning plans, career questions, and projects.', icon: 'ai', action: 'AI mentor', tone: 'teal' },
    { title: 'Courses', detail: 'Browse university courses and open learning materials.', icon: 'courses', action: 'Courses', tone: 'amber' },
    ...(isStudent ? [{ title: 'Daily assessment', detail: 'Practice your skills with a short personalized quiz.', icon: 'assessment', action: 'Daily assessment', tone: 'violet' }] : []),
    { title: 'Projects', detail: 'Find people to build ideas and research together.', icon: 'projects', action: 'Projects', tone: 'blue' },
    { title: 'Hackathons', detail: 'Discover challenges, prizes, and build opportunities.', icon: 'assessment', action: 'Hackathons', tone: 'violet' },
    { title: 'Mentorship', detail: 'Connect with people who can help you grow.', icon: 'mentorship', action: 'Mentorship', tone: 'green' },
    { title: 'Opportunities', detail: 'Explore jobs, internships, fellowships, and more.', icon: 'opportunities', action: 'Opportunities', tone: 'orange' },
    { title: 'Saved posts', detail: 'Return to posts you bookmarked for later.', icon: 'bookmark', action: 'Saved posts', tone: 'slate' },
  ]
  return <section className="explore-page"><div className="explore-grid">{items.map((item) => <button key={item.title} className="explore-card card" onClick={() => onNavigate(item.action)}><span className={`explore-card-icon explore-${item.tone}`}><Icon name={item.icon} size={19} /></span><span className="explore-card-copy"><strong>{item.title}</strong><small>{item.detail}</small></span><span className="explore-arrow">→</span></button>)}</div></section>
}

function CoursesScreen({ token, onNavigate }: { token: string; onNavigate: (destination: string) => void }) {
  const [preferences, setPreferences] = useState<PreferenceData>({ interests: [], goals: [], skills_to_learn: [] })
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => { let active = true; void request<PreferenceData>('/preferences/me', token).then((data) => { if (active) setPreferences(data) }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Could not load your learning goals.') }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [token])
  const searchTerm = topic.trim() || preferences.skills_to_learn[0]?.skill?.name || 'professional skills'
  const resources = [
    { name: 'edX', detail: 'Explore courses from universities and industry partners.', url: `https://www.edx.org/search?q=${encodeURIComponent(searchTerm)}`, tag: 'UNIVERSITY COURSES', icon: 'EX' },
    { name: 'MIT OpenCourseWare', detail: 'Open course materials from MIT subjects and classes.', url: `https://ocw.mit.edu/search/?q=${encodeURIComponent(searchTerm)}`, tag: 'OPEN COURSE MATERIALS', icon: 'MIT' },
    { name: 'freeCodeCamp', detail: 'Follow the free coding curriculum and build practical projects.', url: 'https://www.freecodecamp.org/learn/', tag: 'CODING CURRICULUM', icon: '</>' },
  ]
  return <section className="courses-page"><header className="courses-hero card"><div className="courses-hero-art"><Icon name="courses" size={25} /></div><div><span className="eyebrow">LEARNING PATHS</span><h2>Build your next skill.</h2><p>Explore courses and open learning materials from established education providers.</p></div></header>{error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}<section className="courses-search card"><div><span className="eyebrow">FIND A COURSE</span><h3>What would you like to learn?</h3></div><form onSubmit={(event) => event.preventDefault()}><Icon name="search" size={16} /><input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder={preferences.skills_to_learn[0]?.skill?.name || 'Search a skill or subject'} aria-label="Search courses by skill or subject" /><span>{searchTerm}</span></form>{!topic && preferences.skills_to_learn.length > 0 && <div className="course-skill-chips"><span>From your learning list</span>{preferences.skills_to_learn.slice(0, 6).map((item) => <button key={item.id} onClick={() => setTopic(item.skill?.name || '')}>{item.skill?.name || 'Skill'}</button>)}</div>}{!topic && !loading && preferences.skills_to_learn.length === 0 && <div className="course-goal-prompt">Add skills to your profile to get course searches tailored to what you want to learn. <button onClick={() => onNavigate('My profile')}>Update learning goals <span>→</span></button></div>}</section><div className="courses-section-heading"><div><span className="eyebrow">EXPLORE LEARNING</span><h3>Browse {searchTerm === 'professional skills' ? 'trusted course catalogs' : `courses for ${searchTerm}`}</h3></div><span>Opens in a new tab</span></div><div className="course-provider-grid">{resources.map((resource, index) => <article className={`course-provider card course-provider-${index}`} key={resource.name}><div className="course-provider-top"><span className="course-provider-mark">{resource.icon}</span><span className="course-provider-tag">{resource.tag}</span></div><h3>{resource.name}</h3><p>{resource.detail}</p><a href={resource.url} target="_blank" rel="noreferrer">Browse {resource.name} <span>↗</span></a></article>)}</div><div className="courses-note"><Icon name="news" size={15} /><p>Courses are hosted by their providers. Availability, enrollment, and pricing depend on the course you choose.</p></div></section>
}

type AssessmentOption = { id: string; option_text: string }
type AssessmentQuestion = { id: string; skill_id: string | null; skill_name?: string | null; question_text: string; difficulty: string; points: number; options: AssessmentOption[] }
type DailyAssessment = { id: string; attempt_id: string; assessment_date: string; question_count: number; completed: boolean; answered_count: number; questions: AssessmentQuestion[] }
type AssessmentProgress = { total_completed: number; average_score: number; latest_score: number | null; best_score: number | null }
type AssessmentHistory = { daily_assessment_id: string; attempt_id: string; assessment_date: string; completed: boolean; score: number | null; question_count: number }
type AssessmentResult = { attempt_id: string; score: number; correct_answers: number; total_questions: number; completed_at: string; skill_results: { skill_id: string; skill_name?: string | null; correct: number; total: number; score: number }[] }
function DailyAssessmentScreen({ token, user, onNavigate }: { token: string; user: User; onNavigate: (destination: string) => void }) {
  const [assessment, setAssessment] = useState<DailyAssessment | null>(null)
  const [progress, setProgress] = useState<AssessmentProgress | null>(null)
  const [history, setHistory] = useState<AssessmentHistory[]>([])
  const [result, setResult] = useState<AssessmentResult | null>(null)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [selectedOption, setSelectedOption] = useState('')
  const [savedAnswers, setSavedAnswers] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [answering, setAnswering] = useState(false)
  const [error, setError] = useState('')
  const loadStats = useCallback(async () => { const [nextProgress, nextHistory] = await Promise.all([request<AssessmentProgress>('/daily-assessment/progress', token), request<AssessmentHistory[]>('/daily-assessment/history', token)]); setProgress(nextProgress); setHistory(nextHistory) }, [token])
  const loadAssessment = useCallback(async () => {
    setLoading(true); setError('')
    try { const [today] = await Promise.all([request<DailyAssessment>('/daily-assessment/today', token), loadStats()]); setAssessment(today); setQuestionIndex(Math.min(today.answered_count, Math.max(0, today.questions.length - 1))); setSelectedOption('') }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load today’s assessment.') }
    finally { setLoading(false) }
  }, [loadStats, token])
  useEffect(() => { if (user.role === 'student') void loadAssessment(); else setLoading(false) }, [loadAssessment, user.role])
  const currentQuestion = assessment?.questions[questionIndex]
  async function saveAnswer() {
    if (!assessment || !currentQuestion || !selectedOption) return
    setAnswering(true); setError('')
    try {
      await request(`/daily-assessment/${assessment.attempt_id}/answer`, token, { method: 'POST', body: JSON.stringify({ question_id: currentQuestion.id, selected_option_id: selectedOption }) })
      setSavedAnswers((items) => ({ ...items, [currentQuestion.id]: selectedOption })); setAssessment((today) => today ? { ...today, answered_count: Math.max(today.answered_count, questionIndex + 1) } : today)
      if (questionIndex < assessment.questions.length - 1) { setQuestionIndex((index) => index + 1); setSelectedOption(savedAnswers[assessment.questions[questionIndex + 1]?.id] || '') }
      else {
        const final = await request<AssessmentResult>(`/daily-assessment/${assessment.attempt_id}/submit`, token, { method: 'POST' })
        setResult(final); setAssessment((today) => today ? { ...today, completed: true, answered_count: today.question_count } : today); await loadStats()
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save your answer.') }
    finally { setAnswering(false) }
  }
  const todayHistory = assessment ? history.find((item) => item.attempt_id === assessment.attempt_id) : undefined
  if (user.role !== 'student') return <section className="assessment-locked card"><span className="assessment-icon"><Icon name="assessment" size={24} /></span><h2>Daily assessments are available for student accounts</h2><p>You can still build your learning plan and explore courses from the Courses section.</p><button className="primary-button" onClick={() => onNavigate('Courses')}>Explore courses <span>→</span></button></section>
  return <section className="daily-assessment-page"><header className="assessment-hero card"><div className="assessment-hero-mark"><Icon name="assessment" size={24} /></div><div><span className="eyebrow">A LITTLE PRACTICE, EVERY DAY</span><h2>Daily assessment</h2><p>Short, personalized questions based on the skills you’re building.</p></div><button className="assessment-refresh" onClick={() => void loadAssessment()} disabled={loading}>{loading ? 'Loading…' : '↻ Refresh'}</button></header>{error && <div className="inline-error">{error}{error.toLowerCase().includes('skill') && <button onClick={() => onNavigate('My profile')}>Add skills to profile →</button>}<button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}<div className="assessment-stats"><article className="assessment-stat card"><span>COMPLETED</span><strong>{progress?.total_completed ?? '—'}</strong><small>Daily sessions</small></article><article className="assessment-stat card"><span>AVERAGE SCORE</span><strong>{progress?.total_completed ? `${Math.round(progress.average_score)}%` : '—'}</strong><small>Across completed sessions</small></article><article className="assessment-stat card"><span>PERSONAL BEST</span><strong>{progress?.best_score != null ? `${Math.round(progress.best_score)}%` : '—'}</strong><small>Keep building momentum</small></article></div>{loading ? <div className="assessment-loading card"><span className="loading-spinner" /><p>Preparing your personalized questions…</p></div> : assessment && assessment.completed ? <section className="assessment-complete card"><span className="assessment-complete-mark">✓</span><span className="eyebrow">TODAY’S PRACTICE COMPLETE</span><h3>{result ? `${Math.round(result.score)}%` : todayHistory?.score != null ? `${Math.round(todayHistory.score)}%` : 'Well done'}</h3><p>{result ? `${result.correct_answers} correct out of ${result.total_questions}.` : 'You’ve completed today’s personalized assessment. Come back tomorrow for a new set.'}</p>{result?.skill_results.length ? <div className="assessment-skill-results">{result.skill_results.map((item) => <div key={item.skill_id}><span>{item.skill_name || 'Skill'}</span><strong>{Math.round(item.score)}%</strong></div>)}</div> : null}<button className="secondary-button" onClick={() => onNavigate('Courses')}>Continue learning <span>→</span></button></section> : assessment && currentQuestion ? <section className="assessment-quiz card"><div className="assessment-quiz-top"><div><span className="eyebrow">QUESTION {questionIndex + 1} OF {assessment.questions.length}</span><h3>{currentQuestion.skill_name || 'Your learning path'}</h3></div><span className="assessment-difficulty">{roleName(currentQuestion.difficulty)}</span></div><div className="assessment-progress"><span style={{ width: `${Math.round(((questionIndex + 1) / assessment.questions.length) * 100)}%` }} /></div><p className="assessment-question">{currentQuestion.question_text}</p><div className="assessment-options">{currentQuestion.options.map((option, index) => <button key={option.id} className={selectedOption === option.id ? 'assessment-option selected' : 'assessment-option'} onClick={() => setSelectedOption(option.id)}><span>{String.fromCharCode(65 + index)}</span>{option.option_text}</button>)}</div><footer className="assessment-quiz-footer"><span>{assessment.answered_count} of {assessment.question_count} answers saved</span><button className="primary-button" disabled={!selectedOption || answering} onClick={() => void saveAnswer()}>{answering ? 'Saving…' : questionIndex === assessment.questions.length - 1 ? 'Finish assessment' : 'Save & continue'} <span>→</span></button></footer></section> : !error && <div className="assessment-loading card"><p>No assessment is available today.</p></div>}<section className="assessment-history card"><div className="assessment-history-heading"><div><span className="eyebrow">YOUR PRACTICE</span><h3>Recent assessments</h3></div><span>{history.length} sessions</span></div>{history.length ? <div className="assessment-history-list">{history.slice(0, 6).map((item) => <div key={item.daily_assessment_id}><span className="assessment-history-date">{new Date(`${item.assessment_date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span><span className={item.completed ? 'assessment-history-status complete' : 'assessment-history-status'}>{item.completed ? 'Complete' : 'In progress'}</span><strong>{item.score != null ? `${Math.round(item.score)}%` : '—'}</strong></div>)}</div> : <p className="assessment-history-empty">Complete your first daily assessment to start building your progress history.</p>}</section></section>
}

type NewsArticle = { id: string; title: string; summary?: string | null; image_url?: string | null; category: string; source_name?: string | null; article_url: string; published_at?: string | null; relevance_score: number }
function NewsScreen({ token }: { token: string }) {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { const [items, topics] = await Promise.all([request<NewsArticle[]>('/news/personalized?limit=50', token), request<string[]>('/news/categories', token)]); setArticles(items); setCategories(topics) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load your news feed.') }
    finally { setLoading(false) }
  }, [token])
  useEffect(() => { void load() }, [load])
  async function refresh() {
    setRefreshing(true); setError('')
    try { await request('/news/refresh', token, { method: 'POST' }); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not refresh news.') }
    finally { setRefreshing(false) }
  }
  const visible = selectedCategory === 'All' ? articles : articles.filter((article) => article.category.toLowerCase() === selectedCategory.toLowerCase())
  return <section className="news-page"><header className="news-hero card"><div><span className="eyebrow">RESEARCH, INDUSTRY & IDEAS</span><h2>News for your next big idea.</h2><p>Updates selected around the interests in your CollabVerse profile.</p></div><button className="primary-button" onClick={() => void refresh()} disabled={refreshing}>{refreshing ? 'Refreshing…' : 'Refresh news'} <span>↻</span></button></header>{error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}<div className="news-toolbar"><div className="news-tabs"><button className={selectedCategory === 'All' ? 'active' : ''} onClick={() => setSelectedCategory('All')}>For you</button>{categories.map((category) => <button key={category} className={selectedCategory.toLowerCase() === category.toLowerCase() ? 'active' : ''} onClick={() => setSelectedCategory(category)}>{roleName(category)}</button>)}</div><span>{visible.length} stories</span></div>{loading ? <div className="empty-state card"><div className="comment-loading">Loading your news…</div></div> : visible.length ? <div className="news-list">{visible.map((article) => <NewsArticleCard key={article.id} article={article} />)}</div> : <div className="empty-state card"><div className="empty-illustration"><Icon name="news" size={23} /></div><h2>No stories in this category yet</h2><p>Try another topic or refresh your news feed.</p><button className="primary-button" onClick={() => void refresh()} disabled={refreshing}>Refresh news</button></div>}</section>
}


function NewsArticleCard({ article }: { article: NewsArticle }) {
  const [imageFailed, setImageFailed] = useState(false)
  const published = article.published_at ? new Date(article.published_at) : null
  return <article className="news-post card"><header className="news-post-header"><Avatar name={article.source_name || 'News'} /><div className="news-post-source"><strong>{article.source_name || 'CollabVerse News'}</strong><small>{published ? `${timeAgo(published.toISOString())} · ${published.toLocaleDateString()}` : 'Recent update'}</small></div><span className="news-post-category">{roleName(article.category)}</span></header>{article.image_url && !imageFailed && <a className="news-post-image-link" href={article.article_url} target="_blank" rel="noreferrer" aria-label={`Read: ${article.title}`}><img className="news-post-image" src={article.image_url} alt="" loading="lazy" onError={() => setImageFailed(true)} /></a>}<div className="news-post-body"><h3><a href={article.article_url} target="_blank" rel="noreferrer">{article.title}</a></h3>{article.summary && <p>{article.summary}</p>}</div><footer className="news-post-footer"><span><Icon name="news" size={14} /> Recommended for your interests</span><a href={article.article_url} target="_blank" rel="noreferrer">Read full story <span>↗</span></a></footer></article>
}

function TopNewsWidget({ token, onNavigate }: { token: string; onNavigate: (destination: string) => void }) {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let live = true
    void request<NewsArticle[]>('/news/personalized?limit=5', token)
      .then((items) => { if (live) setArticles(items.slice(0, 5)) })
      .catch(() => { if (live) setArticles([]) })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [token])
  return <section className="top-news-widget card"><header><span><span className="eyebrow">STAY INFORMED</span><h3>Top 5 news</h3></span><span className="top-news-icon"><Icon name="news" size={17} /></span></header>{loading ? <div className="top-news-loading"><span className="loading-spinner" />Finding stories…</div> : articles.length ? <div className="top-news-list">{articles.map((article, index) => <a className="top-news-item" href={article.article_url} target="_blank" rel="noreferrer" key={article.id}><span className="top-news-rank">0{index + 1}</span><span className="top-news-copy"><strong>{article.title}</strong><small>{article.source_name || 'CollabVerse News'} · {article.published_at ? timeAgo(article.published_at) : roleName(article.category)}</small></span>{article.image_url && <img src={article.image_url} alt="" loading="lazy" />}</a>)}</div> : <div className="top-news-empty"><p>Your personalized headlines will appear here.</p></div>}<button className="top-news-all" onClick={() => onNavigate('News')}>View all news <span>→</span></button></section>
}

type MentorType = { id: string; name: string; description: string; premium: boolean }
type AIConversation = { id: string; user_id: string; mentor_type: string; title?: string | null; is_archived: boolean; created_at: string; updated_at: string }
type AIMessage = { id: string; conversation_id: string; sender: string; content: string; created_at: string }
function AIMentorScreen({ token }: { token: string }) {
  const [types, setTypes] = useState<MentorType[]>([])
  const [conversations, setConversations] = useState<AIConversation[]>([])
  const [conversationId, setConversationId] = useState('')
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [mentorType, setMentorType] = useState('general')
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const messagesEnd = useRef<HTMLDivElement>(null)
  const activeType = types.find((type) => type.id === mentorType)
  const loadConversations = useCallback(async () => { const items = await request<AIConversation[]>('/ai/mentor/conversations', token); setConversations(items); return items }, [token])
  useEffect(() => {
    let active = true
    void Promise.all([request<MentorType[]>('/ai/mentor/types', token), loadConversations()]).then(([mentorTypes]) => { if (active) { setTypes(mentorTypes); setMentorType(mentorTypes[0]?.id || 'general') } }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Could not connect to AI mentor.') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [loadConversations, token])
  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, sending])
  async function openConversation(id: string) {
    setConversationId(id); setError('')
    try { const detail = await request<AIConversation & { messages: AIMessage[] }>(`/ai/mentor/conversations/${id}`, token); setMessages(detail.messages); setMentorType(detail.mentor_type) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not open this conversation.') }
  }
  async function startConversation() {
    setError('')
    try { const created = await request<AIConversation>('/ai/mentor/conversations', token, { method: 'POST', body: JSON.stringify({ mentor_type: mentorType }) }); setConversations((items) => [created, ...items]); setConversationId(created.id); setMessages([]) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not start a conversation.') }
  }
  async function send(event: FormEvent) {
    event.preventDefault(); if (!draft.trim() || sending) return
    setSending(true); setError('')
    try {
      let id = conversationId
      if (!id) { const created = await request<AIConversation>('/ai/mentor/conversations', token, { method: 'POST', body: JSON.stringify({ mentor_type: mentorType }) }); id = created.id; setConversationId(id); setConversations((items) => [created, ...items]) }
      const result = await request<{ conversation_id: string; user_message: AIMessage; assistant_message: AIMessage }>(`/ai/mentor/conversations/${id}/messages`, token, { method: 'POST', body: JSON.stringify({ message: draft.trim() }) })
      setMessages((items) => [...items, result.user_message, result.assistant_message]); setDraft('')
      setConversations((items) => items.map((item) => item.id === id ? { ...item, title: item.title || draft.trim().slice(0, 57), updated_at: new Date().toISOString() } : item).sort((a, b) => b.updated_at.localeCompare(a.updated_at)))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'AI mentor could not respond. Please try again.') }
    finally { setSending(false) }
  }
  async function removeConversation(id: string) {
    try { await request(`/ai/mentor/conversations/${id}`, token, { method: 'DELETE' }); setConversations((items) => items.filter((item) => item.id !== id)); if (conversationId === id) { setConversationId(''); setMessages([]) } }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not delete this conversation.') }
  }
  return <section className="ai-mentor-page"><div className="ai-mentor-heading"><div><span className="eyebrow">YOUR PERSONAL LEARNING PARTNER</span><h2>AI mentor</h2><p>Ask questions, work through challenges, and plan your next step.</p></div><label className="mentor-type-select">Mentor focus<select value={mentorType} onChange={(event) => { setMentorType(event.target.value); setConversationId(''); setMessages([]) }}>{types.map((type) => <option key={type.id} value={type.id}>{type.name}{type.premium ? ' · Advanced' : ''}</option>)}</select></label></div>{error && <div className="inline-error">{error}<button onClick={() => setError('')}>×</button></div>}<div className="ai-mentor-layout"><aside className="ai-conversation-rail card"><button className="primary-button" onClick={() => void startConversation()}>+ New conversation</button><span className="eyebrow">RECENT CHATS</span>{loading ? <small>Loading conversations…</small> : conversations.length ? <div className="ai-conversation-list">{conversations.map((conversation) => <div key={conversation.id} className={`ai-conversation-row ${conversation.id === conversationId ? 'selected' : ''}`}><button onClick={() => void openConversation(conversation.id)}><strong>{conversation.title || `${roleName(conversation.mentor_type)} session`}</strong><small>{roleName(conversation.mentor_type)} · {timeAgo(conversation.updated_at)}</small></button><button className="ai-delete-chat" title="Delete conversation" aria-label="Delete conversation" onClick={() => void removeConversation(conversation.id)}>×</button></div>)}</div> : <small>Your conversations will appear here.</small>}</aside><div className="ai-chat-panel card"><header><span className="ai-avatar"><Icon name="ai" size={19} /></span><div><strong>{activeType?.name || 'AI Mentor'}</strong><small>{activeType?.description || 'Thoughtful guidance for your goals.'}</small></div><span className="ai-online">READY</span></header><div className="ai-chat-messages">{messages.length ? messages.map((message) => <div key={message.id} className={`ai-message ${message.sender === 'user' ? 'ai-message-user' : 'ai-message-assistant'}`}><div>{message.content}</div><small>{message.sender === 'user' ? 'You' : 'AI mentor'} · {timeAgo(message.created_at)}</small></div>) : <div className="ai-welcome"><span className="ai-welcome-icon"><Icon name="ai" size={22} /></span><h3>{conversationId ? 'Continue your conversation' : 'What would you like to work through?'}</h3><p>{activeType?.description || 'Ask about your learning, career, research, or project goals.'}</p><div>{['Help me make a learning plan', 'How can I improve my project idea?', 'What should my next career step be?'].map((prompt) => <button key={prompt} onClick={() => setDraft(prompt)}>{prompt}<span>↗</span></button>)}</div></div>}{sending && <div className="ai-thinking"><i /><i /><i /> Mentor is thinking…</div>}<div ref={messagesEnd} /></div><form className="ai-chat-compose" onSubmit={send}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask your mentor anything…" rows={2} maxLength={5000} /><div><small>AI guidance can make mistakes. Use your judgment.</small><button className="primary-button" disabled={!draft.trim() || sending}>{sending ? 'Thinking…' : 'Send'} <span>↑</span></button></div></form></div></div></section>
}

function ProfileScreen({ token, user, setUser, setError, onViewAllProjects }: { token: string; user: User; setUser: (updater: (current: User | null) => User | null) => void; setError: (message: string) => void; onViewAllProjects: () => void }) {
  const [profile, setProfile] = useState<Record<string, unknown>>({})
  const [preferences, setPreferences] = useState<PreferenceData>({ interests: [], goals: [], skills_to_learn: [] })
  const [profilePosts, setProfilePosts] = useState<Post[]>([])
  const [profileProjects, setProfileProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)
  const [interestName, setInterestName] = useState('')
  const [interestCategory, setInterestCategory] = useState('technology')
  const [skillQuery, setSkillQuery] = useState('')
  const [skillResults, setSkillResults] = useState<Skill[]>([])
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)
  const [skillPriority, setSkillPriority] = useState('medium')
  const [busyItem, setBusyItem] = useState('')
  const [avatarUploading, setAvatarUploading] = useState(false)
  const avatarInput = useRef<HTMLInputElement>(null)
  const fields = profileFields[user.role] || profileFields.student

  async function loadProfile() {
    setLoading(true)
    try {
      const [profileResponse, prefs, ownPosts, ownProjects] = await Promise.all([
        request<{ profile: Record<string, unknown>; avatar_url?: string | null }>('/profiles/me', token),
        request<PreferenceData>('/preferences/me', token),
        request<Post[]>(`/posts/users/${user.id}?limit=3&offset=0`, token).catch(() => []),
        request<Project[]>('/projects/me/created', token).catch(() => []),
      ])
      setProfile({ ...(profileResponse.profile || {}), avatar_url: profileResponse.avatar_url || null })
      setPreferences(prefs)
      setProfilePosts(ownPosts)
      setProfileProjects(ownProjects)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load your profile.') }
    finally { setLoading(false) }
  }

  useEffect(() => { void loadProfile() }, [token, user.id])
  async function uploadAvatar(file?: File) {
    if (!file) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) { setError('Choose a JPG, PNG, or WebP image up to 5 MB.'); return }
    setAvatarUploading(true); setError('')
    try {
      const body = new FormData(); body.append('file', file)
      const response = await fetch(`${API}/profiles/me/avatar`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body })
      const result = await response.json().catch(() => null)
      if (!response.ok) throw new Error(result?.detail || 'Could not upload your profile photo.')
      setProfile((current) => ({ ...current, avatar_url: result.avatar_url }))
      setUser((current) => current ? { ...current, avatar_url: result.avatar_url } : current)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not upload your profile photo.') }
    finally { setAvatarUploading(false); if (avatarInput.current) avatarInput.current.value = '' }
  }
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const query = skillQuery.trim()
      const url = query.length >= 2 ? `/skills?search=${encodeURIComponent(query)}` : '/skills'
      void request<Skill[]>(url, token).then(setSkillResults).catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not load skills.'))
    }, skillQuery.trim().length >= 2 ? 250 : 0)
    return () => window.clearTimeout(timer)
  }, [skillQuery, token])

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('')
    const payload: Record<string, unknown> = {}
    for (const field of fields) {
      let value = profile[field.key]
      if (typeof value === 'string' && !value.trim()) value = null
      if (field.kind === 'number' && value !== undefined && value !== null && value !== '') value = Number(value)
      payload[field.key] = value
    }
    const patchRole = user.role === 'institution_admin' ? 'institution' : user.role
    try {
      const result = await request<{ profile: Record<string, unknown> }>(`/profiles/me/${patchRole}`, token, { method: 'PATCH', body: JSON.stringify(payload) })
      setProfile(result.profile)
      const displayName = String(result.profile.full_name || result.profile.admin_name || '')
      setUser((current) => current ? { ...current, profile: { ...current.profile, ...result.profile, full_name: displayName } } : current)
      setEditing(false)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save your profile.') }
    finally { setSaving(false) }
  }

  async function chooseInterest(name: string, category: string) {
    if (preferences.interests.some((item) => item.name.toLowerCase() === name.toLowerCase())) return
    setBusyItem('interest'); setError('')
    try {
      const added = await request<Interest>('/preferences/interests', token, { method: 'POST', body: JSON.stringify({ name, category }) })
      setPreferences((current) => ({ ...current, interests: [...current.interests, added] })); setInterestName('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not add this interest.') }
    finally { setBusyItem('') }
  }

  async function addLearningSkill() {
    if (!selectedSkill) return
    setBusyItem('skill'); setError('')
    try {
      const added = await request<Learning>('/preferences/learning-skills', token, { method: 'POST', body: JSON.stringify({ skill_id: selectedSkill.id, priority: skillPriority }) })
      setPreferences((current) => ({ ...current, skills_to_learn: [...current.skills_to_learn, added] })); setSelectedSkill(null); setSkillQuery(''); setSkillResults([])
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not add this skill.') }
    finally { setBusyItem('') }
  }

  async function removePreference(kind: 'interests' | 'goals' | 'learning-skills', id: string) {
    setBusyItem(id); setError('')
    try {
      await request(`/preferences/${kind}/${id}`, token, { method: 'DELETE' })
      if (kind === 'interests') setPreferences((current) => ({ ...current, interests: current.interests.filter((item) => item.id !== id) }))
      if (kind === 'goals') setPreferences((current) => ({ ...current, goals: current.goals.filter((item) => item.id !== id) }))
      if (kind === 'learning-skills') setPreferences((current) => ({ ...current, skills_to_learn: current.skills_to_learn.filter((item) => item.id !== id) }))
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not remove this item.') }
    finally { setBusyItem('') }
  }

  function cancelProfileEdit() {
    setEditing(false)
    void loadProfile()
  }

  const displayName = String(profile.full_name || profile.admin_name || user.profile?.full_name || user.email.split('@')[0])
  const displayHeadline = String(profile.headline || profile.designation || profile.company_name || profile.institution_name || `${roleName(user.role)} · CollabVerse`)
  const aboutText = String(profile.bio || profile.research_interests || profile.career_goal || '')
  const detailFields = fields.filter((field) => !['full_name', 'admin_name', 'bio', 'research_interests', 'career_goal'].includes(field.key) && profile[field.key] !== undefined && profile[field.key] !== null && String(profile[field.key]).trim())
  const filledFields = fields.filter((field) => { const value = profile[field.key]; return value !== undefined && value !== null && String(value).trim().length > 0 }).length
  const profileCompletion = Math.round(((filledFields + (profile.avatar_url || user.avatar_url ? 1 : 0) + Math.min(preferences.interests.length > 0 ? 1 : 0, 1) + Math.min(preferences.goals.length > 0 ? 1 : 0, 1) + Math.min(preferences.skills_to_learn.length > 0 ? 1 : 0, 1)) / (fields.length + 4)) * 100)
  const requiredProfileKeys = ['full_name', 'admin_name', ...(user.role === 'recruiter' ? ['company_name'] : []), ...(user.role === 'institution_admin' ? ['institution_name'] : [])]
  const availableInterests = (interestTopicsByCategory[interestCategory] || []).filter((name) => name.toLowerCase().includes(interestName.trim().toLowerCase()) && !preferences.interests.some((item) => item.name.toLowerCase() === name.toLowerCase()))

  return <section className="profile-page">
    <div className="profile-hero card"><div className="profile-hero-cover" /><div className="profile-hero-body"><div className="profile-avatar-edit"><Avatar name={displayName} large imageUrl={String(profile.avatar_url || user.avatar_url || '')} /><button type="button" onClick={() => avatarInput.current?.click()} disabled={avatarUploading} aria-label="Change profile photo">{avatarUploading ? '…' : '✎'}</button><input ref={avatarInput} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(event) => void uploadAvatar(event.currentTarget.files?.[0])} /></div><div className="profile-hero-copy"><span className="eyebrow">YOUR PROFESSIONAL PROFILE</span><h2>{displayName}</h2><p>{displayHeadline}</p><span className="role-pill">{roleName(user.role)}</span></div><div className="profile-hero-actions"><button type="button" className="profile-edit-toggle" onClick={() => editing ? cancelProfileEdit() : setEditing(true)}>{editing ? 'Cancel editing' : 'Edit profile'} <span>{editing ? '×' : '✎'}</span></button></div><div className="profile-completion"><span>PROFILE STRENGTH</span><strong>{profileCompletion}% complete</strong><div className="profile-completion-track"><span style={{ width: `${profileCompletion}%` }} /></div><small>Complete your profile, interests, and goals.</small></div></div></div>
    {loading ? <div className="profile-loading card">Loading your profile…</div> : <>
      <div className="profile-layout" style={{ display: editing ? undefined : 'none' }}>
      <div className="profile-main-column">
        <form className="profile-section card" onSubmit={saveProfile}><div className="section-heading"><div><span className="eyebrow">INTRODUCTION</span><h3>Profile details</h3><p>Tell the community who you are and what you do.</p></div><span className="section-icon">◉</span></div><div className="profile-fields">{fields.map((field) => <label key={field.key} className={field.wide ? 'profile-field field-wide' : 'profile-field'}>{field.label}{field.kind === 'textarea' ? <><textarea rows={4} value={String(profile[field.key] ?? '')} placeholder={field.hint || `Add your ${field.label.toLowerCase()}`} onChange={(event) => setProfile((current) => ({ ...current, [field.key]: event.target.value }))} /></> : <input type={field.kind || 'text'} min={field.kind === 'number' ? 0 : undefined} max={field.key === 'graduation_year' ? 2100 : undefined} value={String(profile[field.key] ?? '')} required={requiredProfileKeys.includes(field.key)} placeholder={field.hint || `Add ${field.label.toLowerCase()}`} onChange={(event) => setProfile((current) => ({ ...current, [field.key]: event.target.value }))} />}</label>)}</div><div className="profile-form-footer"><span>Only share details you’re comfortable making part of your professional profile.</span><button className="primary-button" disabled={saving}>{saving ? 'Saving…' : 'Save profile'} <span>↗</span></button></div></form>
      </div>
      <div className="profile-side-column">
        <section className="profile-section card"><div className="section-heading compact"><div><span className="eyebrow">YOUR CURIOSITIES</span><h3>Interests</h3><p>Choose topics from a scrollable list.</p></div><span className="section-icon violet">✳</span></div><div className="profile-option-controls"><select value={interestCategory} onChange={(event) => { setInterestCategory(event.target.value); setInterestName('') }} aria-label="Interest category">{interestCategories.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><input value={interestName} onChange={(event) => setInterestName(event.target.value)} placeholder="Filter interests" aria-label="Filter interests" /></div><div className="profile-choice-list" role="listbox" aria-label="Available interests">{availableInterests.map((name) => <button type="button" role="option" aria-selected="false" key={name} onClick={() => void chooseInterest(name, interestCategory)} disabled={busyItem === 'interest'}><span>{name}</span><span className="profile-choice-add">+</span></button>)}{availableInterests.length === 0 && <div className="section-empty">No more matching interests in this category.</div>}</div><div className="profile-selected-list">{preferences.interests.map((item) => <div className="profile-selected-row" key={item.id}><span><strong>{item.name}</strong><small>{roleName(item.category)}</small></span><button className="remove-item" onClick={() => void removePreference('interests', item.id)} aria-label={`Remove ${item.name}`} disabled={busyItem === item.id}>Remove</button></div>)}{preferences.interests.length === 0 && <div className="section-empty">Your selected interests will appear here.</div>}</div></section>
        <section className="profile-section card"><div className="section-heading compact"><div><span className="eyebrow">GROW YOUR EXPERTISE</span><h3>Skills to learn</h3><p>Browse the list or search for a skill.</p></div><span className="section-icon teal">⌘</span></div><div className="profile-option-controls skill-controls"><input value={selectedSkill?.name || skillQuery} onChange={(event) => { setSelectedSkill(null); setSkillQuery(event.target.value) }} placeholder="Search skills" aria-label="Search skills" /><select value={skillPriority} onChange={(event) => setSkillPriority(event.target.value)} aria-label="Learning priority"><option value="high">High priority</option><option value="medium">Medium</option><option value="low">Low</option></select></div><div className="profile-choice-list skill-choice-list" role="listbox" aria-label="Available skills">{skillResults.filter((skill) => !preferences.skills_to_learn.some((item) => item.skill_id === skill.id)).map((skill) => <button type="button" role="option" aria-selected={selectedSkill?.id === skill.id} className={selectedSkill?.id === skill.id ? 'selected' : ''} key={skill.id} onClick={() => setSelectedSkill(skill)}><span>{skill.name}<small>{roleName(skill.category)}</small></span><span className="profile-choice-add">{selectedSkill?.id === skill.id ? '✓' : '+'}</span></button>)}{skillResults.length === 0 && <div className="section-empty">No matching skills found in the catalog.</div>}</div><button className="skill-add-button" onClick={() => void addLearningSkill()} disabled={!selectedSkill || busyItem === 'skill'}>Add selected skill <span>+</span></button><div className="profile-selected-list learning-list">{preferences.skills_to_learn.map((item) => <div className="profile-selected-row" key={item.id}><span><strong>{item.skill?.name || 'Skill'}</strong><small>{roleName(item.priority)} priority</small></span><button className="remove-item" aria-label={`Remove ${item.skill?.name || 'skill'}`} onClick={() => void removePreference('learning-skills', item.id)} disabled={busyItem === item.id}>Remove</button></div>)}{preferences.skills_to_learn.length === 0 && <div className="section-empty">Your learning list is empty for now.</div>}</div></section>
      </div>
      </div>
      {!editing && <div className="profile-overview">
        <div className="profile-overview-main">
          <section className="profile-section card"><div className="section-heading"><div><span className="eyebrow">ABOUT</span><h3>A little about me</h3></div><span className="section-icon">◉</span></div><p className="profile-about-copy">{aboutText || 'Add a short introduction to help people in your community get to know you.'}</p>{detailFields.length > 0 && <div className="profile-overview-details">{detailFields.map((field) => <div key={field.key}><small>{field.label}</small><strong>{String(profile[field.key])}</strong></div>)}</div>}</section>
          <section className="profile-section card"><div className="profile-overview-section-heading"><div><span className="eyebrow">MY WORK</span><h3>Projects</h3><p>Your latest collaborations and ideas.</p></div><span className="section-icon"><Icon name="projects" size={16} /></span></div>{profileProjects.length ? <div className="profile-project-list">{profileProjects.slice(0, 3).map((project) => <article className="profile-project-item" key={project.id}><span className="profile-project-icon"><Icon name="projects" size={15} /></span><div><strong>{project.title}</strong><small>{project.domain || roleName(project.project_type)} · {roleName(project.status)}</small><p>{project.description}</p></div></article>)}</div> : <p className="profile-section-empty">Your projects will show up here when you create or join one.</p>}<button type="button" className="profile-view-all" onClick={onViewAllProjects}>View all my projects <span>→</span></button></section>
          <section className="profile-section card"><div className="profile-overview-section-heading"><div><span className="eyebrow">MY UPDATES</span><h3>Posts</h3><p>Recent things I’ve shared with the community.</p></div><span className="profile-section-count">{profilePosts.length}</span></div>{profilePosts.length ? <div className="profile-post-list">{profilePosts.map((post) => <article className="profile-post-item" key={post.id}>{post.content && <p>{post.content}</p>}{post.media?.length ? <div className="profile-post-media">{post.media.slice(0, 3).map((media) => media.media_type === 'video' ? <video key={media.id} src={media.media_url} controls preload="metadata" /> : <img key={media.id} src={media.media_url} alt="My post upload" loading="lazy" />)}</div> : null}<small>{timeAgo(post.created_at)} · {post.like_count} appreciations · {post.comment_count} comments</small></article>)}</div> : <p className="profile-section-empty">Your posts will appear here after you share an update.</p>}</section>
        </div>
        <aside className="profile-overview-side">
          <section className="profile-section card"><div className="section-heading compact"><div><span className="eyebrow">YOUR CURIOSITIES</span><h3>Interests</h3></div><span className="section-icon violet">✳</span></div>{preferences.interests.length ? <div className="profile-overview-tags">{preferences.interests.map((item) => <span key={item.id}>{item.name}<small>{roleName(item.category)}</small></span>)}</div> : <p className="profile-section-empty">Your interests will appear here.</p>}</section>
          <section className="profile-section card"><div className="section-heading compact"><div><span className="eyebrow">WHAT I’M WORKING TOWARD</span><h3>Goals</h3></div><span className="section-icon gold">◎</span></div>{preferences.goals.length ? <div className="profile-overview-goals">{preferences.goals.map((goal) => <div key={goal.id}><strong>{goal.title}</strong><small>{roleName(goal.goal_type)}</small></div>)}</div> : <p className="profile-section-empty">Your goals will appear here.</p>}</section>
          {preferences.skills_to_learn.length > 0 && <section className="profile-section card"><div className="section-heading compact"><div><span className="eyebrow">GROWING MY EXPERTISE</span><h3>Skills to learn</h3></div><span className="section-icon teal">⌘</span></div><div className="profile-overview-goals">{preferences.skills_to_learn.map((item) => <div key={item.id}><strong>{item.skill?.name || 'Skill'}</strong><small>{roleName(item.priority)} priority</small></div>)}</div></section>}
        </aside>
      </div>}
    </>}
  </section>
}

function OnboardingScreen({ token, user, onComplete }: { token: string; user: User; onComplete: () => void }) {
  const [step, setStep] = useState(0)
  const [profile, setProfile] = useState<Record<string, unknown>>({})
  const [preferences, setPreferences] = useState<PreferenceData>({ interests: [], goals: [], skills_to_learn: [] })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [message, setMessage] = useState('')
  const [interestSearch, setInterestSearch] = useState('')
  const [interestSearchOpen, setInterestSearchOpen] = useState(false)
  const [interestCategory, setInterestCategory] = useState(interestDomainsByRole[user.role]?.[0] || 'technology')
  const [goalTitle, setGoalTitle] = useState('')
  const [goalType, setGoalType] = useState('career')
  const [busy, setBusy] = useState(false)
  const fields = profileFields[user.role] || profileFields.student
  const interestSearchResults = interestOptions
    .filter((option) => option.category === interestCategory)
    .filter((option) => !interestSearch.trim() || option.name.toLowerCase().includes(interestSearch.trim().toLowerCase()))
    .filter((option) => !preferences.interests.some((item) => item.name.toLowerCase() === option.name.toLowerCase() && item.category === option.category))
    .slice(0, 8)
  const hasExactInterestOption = interestOptions.some((option) => option.category === interestCategory && option.name.toLowerCase() === interestSearch.trim().toLowerCase())
  const displayName = String(profile.full_name || profile.admin_name || user.profile?.full_name || user.email.split('@')[0])
  const steps = [
    { title: 'A little about you', subtitle: 'Set up the profile people in your community will see.' },
    { title: 'What interests you?', subtitle: 'Choose topics you want to explore with your professional community.' },
    { title: 'What are your goals?', subtitle: 'Tell us what you are working toward so we can make your feed more relevant.' },
  ]

  async function loadSetup() {
    setLoading(true); setMessage('')
    try {
      const [profileResponse, prefs] = await Promise.all([
        request<{ profile: Record<string, unknown> }>('/profiles/me', token),
        request<PreferenceData>('/preferences/me', token),
      ])
      setProfile(profileResponse.profile || {})
      setPreferences(prefs)
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Could not load your setup.') }
    finally { setLoading(false) }
  }

  useEffect(() => { void loadSetup() }, [token])
  async function saveProfileStep() {
    setSaving(true); setMessage('')
    const payload: Record<string, unknown> = {}
    for (const field of fields) {
      let value = profile[field.key]
      if (value === undefined || value === null || value === '') continue
      if (field.kind === 'number') value = Number(value)
      payload[field.key] = value
    }
    const patchRole = user.role === 'institution_admin' ? 'institution' : user.role
    try {
      const result = await request<{ profile: Record<string, unknown> }>(`/profiles/me/${patchRole}`, token, { method: 'PATCH', body: JSON.stringify(payload) })
      setProfile(result.profile)
      setStep(1)
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Could not save your profile.') }
    finally { setSaving(false) }
  }

  async function addInterest(name: string, category = interestCategory): Promise<boolean> {
    if (!name.trim()) return false
    if (preferences.interests.some((item) => item.name.toLowerCase() === name.toLowerCase() && item.category === category)) return true
    setBusy(true); setMessage('')
    try {
      const created = await request<Interest>('/preferences/interests', token, { method: 'POST', body: JSON.stringify({ name: name.trim(), category }) })
      setPreferences((current) => ({ ...current, interests: [...current.interests, created] }))
      return true
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Could not add this interest.'); return false }
    finally { setBusy(false) }
  }

  async function addCustomInterest() {
    if (await addInterest(interestSearch, interestCategory)) { setInterestSearch(''); setInterestSearchOpen(false) }
  }

  async function chooseInterest(option: { name: string; category: string }) {
    if (await addInterest(option.name, option.category)) { setInterestSearch(''); setInterestSearchOpen(false) }
  }

  async function addGoal(event: FormEvent) {
    event.preventDefault(); if (!goalTitle.trim()) return
    setBusy(true); setMessage('')
    try {
      const created = await request<Goal>('/preferences/goals', token, { method: 'POST', body: JSON.stringify({ title: goalTitle.trim(), goal_type: goalType, priority: 2 }) })
      setPreferences((current) => ({ ...current, goals: [created, ...current.goals] })); setGoalTitle('')
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Could not add this goal.') }
    finally { setBusy(false) }
  }

  async function removeInterest(id: string) {
    setBusy(true); setMessage('')
    try { await request(`/preferences/interests/${id}`, token, { method: 'DELETE' }); setPreferences((current) => ({ ...current, interests: current.interests.filter((item) => item.id !== id) })) }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Could not remove this interest.') }
    finally { setBusy(false) }
  }

  async function removeItem(kind: 'goals' | 'learning-skills', id: string) {
    setBusy(true); setMessage('')
    try {
      await request(`/preferences/${kind}/${id}`, token, { method: 'DELETE' })
      if (kind === 'goals') setPreferences((current) => ({ ...current, goals: current.goals.filter((item) => item.id !== id) }))
      else setPreferences((current) => ({ ...current, skills_to_learn: current.skills_to_learn.filter((item) => item.id !== id) }))
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : 'Could not remove this item.') }
    finally { setBusy(false) }
  }

  function next() { setMessage(''); setStep((current) => Math.min(current + 1, steps.length - 1)) }
  function finish() { setFinishing(true); window.setTimeout(onComplete, 650) }

  if (finishing) return <main className="onboarding-finish"><div className="finish-orbit"><span>✓</span></div><span className="eyebrow">YOU’RE ALL SET</span><h1>Your community is ready, {displayName.split(' ')[0]}.</h1><p>Bringing your network together…</p><div className="finish-progress"><span /></div></main>

  return <main className="onboarding-page">
    <header className="onboarding-header"><BrandLogo href="#" /><div className="onboarding-save-note"><span className="save-check">✓</span> Your answers save as you go</div></header>
    <div className="onboarding-wrap">
      <div className="onboarding-progress"><span>SET UP YOUR SPACE</span><strong>STEP {step + 1} <i>/</i> {steps.length}</strong><div className="progress-track">{steps.map((item, index) => <span key={item.title} className={index <= step ? 'progress-active' : ''} />)}</div></div>
      {message && <div className="onboarding-error">{message}<button onClick={() => setMessage('')}>×</button></div>}
      {loading ? <div className="onboarding-card onboarding-loading"><span className="loading-spinner" /><strong>Preparing your profile</strong><p>Getting your space ready…</p></div> : <div key={step} className="onboarding-card onboarding-step">
        <div className="onboarding-step-icon">{['◉', '✳', '◎'][step]}</div><div className="eyebrow">{['YOUR PROFILE', 'YOUR INTERESTS', 'YOUR DIRECTION'][step]}</div><h1>{steps[step].title}</h1><p className="onboarding-intro">{steps[step].subtitle}</p>
        {step === 0 && <div className="onboarding-profile-fields">{fields.map((field) => <label key={field.key} className={field.wide ? 'onboarding-field field-wide' : 'onboarding-field'}>{field.label}{field.kind === 'textarea' ? <textarea rows={3} value={String(profile[field.key] ?? '')} placeholder={field.hint || `Add your ${field.label.toLowerCase()}`} onChange={(event) => setProfile((current) => ({ ...current, [field.key]: event.target.value }))} /> : <input type={field.kind || 'text'} min={field.kind === 'number' ? 0 : undefined} value={String(profile[field.key] ?? '')} placeholder={`Add ${field.label.toLowerCase()}`} onChange={(event) => setProfile((current) => ({ ...current, [field.key]: event.target.value }))} />}</label>)}</div>}
        {step === 1 && <><div className="onboard-interest-search"><div className="onboard-interest-search-row"><select value={interestCategory} onChange={(event) => { setInterestCategory(event.target.value); setInterestSearch(''); setInterestSearchOpen(true) }} aria-label="Interest domain">{interestCategories.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><input value={interestSearch} onFocus={() => setInterestSearchOpen(true)} onBlur={() => window.setTimeout(() => setInterestSearchOpen(false), 120)} onChange={(event) => { setInterestSearch(event.target.value); setInterestSearchOpen(true) }} placeholder={`Search ${roleName(interestCategory)} interests`} maxLength={150} aria-label="Search interests" />{interestSearch.trim() && !hasExactInterestOption && <button type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => void addCustomInterest()} disabled={busy}>Add</button>}</div>{interestSearchOpen && <div className="onboard-interest-results">{interestSearchResults.map((option) => <button type="button" key={`${option.category}-${option.name}`} onMouseDown={(event) => event.preventDefault()} onClick={() => void chooseInterest(option)} disabled={busy}><span>{option.name}</span></button>)}{interestSearch.trim() && !hasExactInterestOption && <div className="onboard-custom-hint">Add “{interestSearch.trim()}” to {roleName(interestCategory)}.</div>}</div>}</div><div className="onboard-suggestion-label">YOUR INTERESTS</div><div className="interest-tags onboard-tags">{preferences.interests.map((item) => <span className="interest-tag" key={item.id}>{item.name}<small>{roleName(item.category)}</small><button onClick={() => void removeInterest(item.id)} disabled={busy} aria-label={`Remove ${item.name}`}>×</button></span>)}{preferences.interests.length === 0 && <span className="onboard-empty">Search and choose topics, or add a custom interest.</span>}</div></>}
        {step === 2 && <><form className="onboard-add-row" onSubmit={addGoal}><input value={goalTitle} onChange={(event) => setGoalTitle(event.target.value)} placeholder="Add a goal you’re working toward" maxLength={255} /><select value={goalType} onChange={(event) => setGoalType(event.target.value)} aria-label="Goal type">{goalTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button disabled={!goalTitle.trim() || busy}>Add</button></form><div className="onboard-suggestion-label">YOUR GOALS</div><div className="onboard-list">{preferences.goals.map((goal) => <div className="goal-row" key={goal.id}><span className="goal-check">↗</span><div><strong>{goal.title}</strong><small>{roleName(goal.goal_type)} goal</small></div><button className="remove-item" onClick={() => void removeItem('goals', goal.id)} disabled={busy} aria-label={`Remove ${goal.title}`}>×</button></div>)}{preferences.goals.length === 0 && <span className="onboard-empty">Add one or more goals to help personalize your experience.</span>}</div></>}
        <div className="onboarding-footer"><button className="onboarding-back" onClick={() => { setMessage(''); setStep((current) => Math.max(0, current - 1)) }} disabled={step === 0}>← <span>Back</span></button><span className="onboarding-step-caption">{step + 1} of {steps.length}</span>{step === 0 ? <button className="onboarding-next" onClick={() => void saveProfileStep()} disabled={saving}>{saving ? 'Saving…' : 'Continue'} <span>→</span></button> : step < steps.length - 1 ? <button className="onboarding-next" onClick={next}>Continue <span>→</span></button> : <button className="onboarding-next" onClick={finish}>Go to my feed <span>→</span></button>}</div>
      </div>}
      <div className="onboarding-footnote"><span>✳</span> Your profile helps the right people and opportunities find you.</div>
    </div>
  </main>
}

function AuthScreen({ mode, setMode, onSubmit, error, googleSignupCode }: { mode: 'login' | 'register'; setMode: (mode: 'login' | 'register') => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; error: string; googleSignupCode: string }) {
  const [role, setRole] = useState('student')
  const [legal, setLegal] = useState<'terms' | 'privacy' | null>(null)
  const googleSignup = mode === 'register' && Boolean(googleSignupCode)
  return <main className="auth-page">
    <header className="auth-topbar"><BrandLogo href="#" /><span>Academia meets industry.</span></header>
    <div className="auth-layout">
      <section className="auth-pitch"><span className="eyebrow">A COMMUNITY FOR WHAT’S NEXT</span><h1>Good work<br />moves <em>forward</em><br />together.</h1><p>Connect with researchers, builders, and industry leaders. Share ideas, find collaborators, and turn ambition into impact.</p><div className="pitch-points"><span><b>01</b> Meet people beyond your discipline</span><span><b>02</b> Share what you’re building</span><span><b>03</b> Find your next opportunity</span></div><div className="auth-orbit orbit-one" /><div className="auth-orbit orbit-two" /><div className="auth-star">✳</div></section>
      <section className="auth-card card">
        <div className="auth-card-top"><div className="auth-symbol">↗</div><div className="eyebrow">WELCOME TO COLLABVERSE</div><h2>{mode === 'login' ? 'Sign in to your community' : googleSignup ? 'Finish creating your account' : 'Create your account'}</h2><p>{googleSignup ? 'Your Google email is verified. Add your profile details and set a password for future sign-ins.' : mode === 'login' ? 'Sign in with your email and password, or continue with Google.' : 'Verify your email with Google to create a CollabVerse account.'}</p></div>
        {error && <div className="inline-error" role="status">{error}</div>}
        {!googleSignup && mode === 'login' && <><form onSubmit={onSubmit} className="auth-form"><label>Email<input name="email" type="email" placeholder="you@example.com" required autoComplete="email" /></label><label>Password<input name="password" type="password" required autoComplete="current-password" /></label><button className="auth-submit">Sign in <span>→</span></button></form><div className="auth-divider"><span>or</span></div><button type="button" className="google-auth-button" onClick={() => { window.location.assign(`${API}/auth/google/login`) }}><span className="google-g" aria-hidden="true">G</span>Continue with Google</button></>}
        {!googleSignup && mode === 'register' && <button type="button" className="google-auth-button" onClick={() => { window.location.assign(`${API}/auth/google/login`) }}><span className="google-g" aria-hidden="true">G</span>Verify with Google to sign up</button>}
        {googleSignup && <form onSubmit={onSubmit} className="auth-form"><label>Full name<input name="name" placeholder="e.g. Rishabh Jangra" required autoComplete="name" /></label><label>Your role<select name="role" value={role} onChange={(event) => setRole(event.target.value)}><option value="student">Student</option><option value="professional">Industry professional</option><option value="recruiter">Recruiter</option><option value="academician">Academician</option><option value="institution_admin">Institution administrator</option></select></label>{role !== 'student' && role !== 'professional' && <label>{role === 'recruiter' ? 'Company' : 'Institution'}<input name="organization" placeholder={role === 'recruiter' ? 'Company name' : 'Institution name'} required /></label>}<label>Password<input name="password" type="password" placeholder="At least 8 characters" minLength={8} maxLength={128} required autoComplete="new-password" /></label><label className="auth-honeypot" aria-hidden="true">Leave this field empty<input name="website" tabIndex={-1} autoComplete="off" /></label><div className="auth-terms-check"><input name="accepted_terms" type="checkbox" required /><span>I agree to the <button type="button" onClick={() => setLegal('terms')}>Terms of Service</button> and have read the <button type="button" onClick={() => setLegal('privacy')}>Privacy Policy</button>.</span></div><button className="auth-submit">Create account <span>→</span></button></form>}
        <div className="auth-switch">{mode === 'login' ? 'New to CollabVerse?' : 'Already have an account?'} <button onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></div>
        {mode === 'login' && <div className="auth-legal"><button onClick={() => setLegal('terms')}>Terms of Service</button><span>·</span><button onClick={() => setLegal('privacy')}>Privacy Policy</button></div>}
      </section>
    </div>
    <footer className="auth-footer">© 2026 CollabVerse <span>·</span> Built for collaboration</footer>
    {legal && <div className="auth-legal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setLegal(null) }}><section className="auth-legal-dialog card" role="dialog" aria-modal="true" aria-labelledby="auth-legal-title"><button type="button" className="auth-legal-close" onClick={() => setLegal(null)} aria-label="Close">×</button><span className="eyebrow">COLLABVERSE</span><h2 id="auth-legal-title">{legal === 'terms' ? 'Terms of Service' : 'Privacy Policy'}</h2>{legal === 'terms' ? <div className="auth-legal-copy"><p><strong>Using CollabVerse.</strong> CollabVerse helps students, academics, and professionals connect, learn, share work, and collaborate. By creating an account, you agree to use the service lawfully and respectfully.</p><p><strong>Your account.</strong> Provide accurate information, keep your sign-in credentials secure, and do not impersonate another person or create accounts to mislead or disrupt the community.</p><p><strong>Community content.</strong> You retain responsibility for what you post and must have the rights to share it. Do not post unlawful, abusive, deceptive, or harmful material, or use the service to spam or harass others.</p><p><strong>Mentoring and collaboration.</strong> Users are responsible for evaluating people, opportunities, and advice they receive. CollabVerse does not guarantee a particular outcome from an introduction, project, or mentorship.</p><p><strong>Safety and enforcement.</strong> We may review reports and restrict accounts or content that violate these terms or threaten the community. You may stop using the service and request account support through the platform.</p><p><strong>Service changes.</strong> Features may change as the platform develops. We will update these terms when needed and show the current version during account creation.</p></div> : <div className="auth-legal-copy"><p><strong>Information you provide.</strong> We use account details, profile information, interests, goals, posts, messages, and uploaded media to provide CollabVerse features.</p><p><strong>How information is used.</strong> Profile and activity information supports discovery, connections, recommendations, mentoring, messaging, and community safety.</p><p><strong>Your choices.</strong> Keep your profile accurate, share only content you are comfortable placing on the service, and contact the platform team to request help with your account or data.</p><p><strong>Security and sharing.</strong> We use safeguards designed to protect account information. Some information is visible to other members when you use community features; avoid sharing sensitive personal information in public areas.</p><p><strong>Updates.</strong> This policy may change as CollabVerse adds features. The version shown here describes the current project policy.</p></div>}<button type="button" className="primary-button auth-legal-done" onClick={() => setLegal(null)}>Close</button></section></div>}
  </main>
}
