import { useAuth } from '../auth/authContext';

const nextSteps = [
  {
    label: 'Profile',
    title: 'Shape your wellness space',
    body: 'Choose the areas and preferences that matter to you.',
  },
  {
    label: 'Records',
    title: 'Capture everyday context',
    body: 'Add structured observations from sleep, movement, mood, and more.',
  },
  {
    label: 'Goals',
    title: 'Keep intentions in view',
    body: 'Define personal goals without judgment or prescriptive scoring.',
  },
  {
    label: 'Wellness summary',
    title: 'Understand your patterns',
    body: 'Review transparent baselines and mathematical trends over time.',
  },
];

export function DashboardPage() {
  const { user } = useAuth();
  if (!user) {
    return null;
  }

  const hasProfile = user.profile_ids.length > 0;

  return (
    <div className="dashboard">
      <section className="dashboard__welcome" aria-labelledby="dashboard-title">
        <div>
          <p className="eyebrow">Your LifeLenz space</p>
          <h1 id="dashboard-title">
            Welcome. Your everyday context starts here.
          </h1>
          <p>
            You’re signed in as <strong>{user.email}</strong>. This foundation
            is ready for the next focused wellness workflows.
          </p>
        </div>
        <div
          className={`profile-status profile-status--${hasProfile ? 'ready' : 'pending'}`}
        >
          <span className="profile-status__dot" aria-hidden="true" />
          <div>
            <span className="profile-status__label">Wellness profile</span>
            <strong>{hasProfile ? 'Configured' : 'Not configured yet'}</strong>
          </div>
        </div>
      </section>

      <section
        className="dashboard__next"
        aria-labelledby="coming-next-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Foundation ready</p>
            <h2 id="coming-next-heading">Coming next</h2>
          </div>
          <p>
            These focused experiences are planned, but are not available in this
            release.
          </p>
        </div>
        <div className="next-grid">
          {nextSteps.map((step, index) => (
            <article className="next-card" key={step.label}>
              <span className="next-card__number">0{index + 1}</span>
              <span className="next-card__status">Coming next</span>
              <p className="next-card__label">{step.label}</p>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
