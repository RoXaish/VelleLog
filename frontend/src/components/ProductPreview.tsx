import React from 'react';

const DAY_START = 14;
const DAY_END = 22;

const SHARED_WINDOW = { start: 18.5, end: 20 };

const HOUR_LABELS = ['2 PM', '4 PM', '6 PM', '8 PM', '10 PM'];

const pct = (hour: number) => ((hour - DAY_START) / (DAY_END - DAY_START)) * 100;

type SegmentKind = 'free' | 'busy';

interface ScheduleSegment {
  start: number;
  end: number;
  kind: SegmentKind;
}

interface DemoMember {
  name: string;
  initials: string;
  status: string;
  free: boolean;
  gradient: [string, string];
  segments: ScheduleSegment[];
}

const MEMBERS: DemoMember[] = [
  {
    name: 'Alex',
    initials: 'AL',
    status: 'Free',
    free: true,
    gradient: ['#ffd9a0', '#ff8a5c'],
    segments: [
      { start: 14, end: 17.25, kind: 'free' },
      { start: 17.25, end: 18.5, kind: 'busy' },
      { start: 18.5, end: 22, kind: 'free' },
    ],
  },
  {
    name: 'Sam',
    initials: 'SA',
    status: 'Busy',
    free: false,
    gradient: ['#ffa38a', '#ff5f45'],
    segments: [
      { start: 14, end: 18.5, kind: 'busy' },
      { start: 18.5, end: 22, kind: 'free' },
    ],
  },
  {
    name: 'Jordan',
    initials: 'JO',
    status: 'Free',
    free: true,
    gradient: ['#ffc27a', '#ff7a59'],
    segments: [
      { start: 14, end: 16, kind: 'free' },
      { start: 16, end: 18, kind: 'busy' },
      { start: 18, end: 22, kind: 'free' },
    ],
  },
  {
    name: 'Taylor',
    initials: 'TA',
    status: 'Free',
    free: true,
    gradient: ['#ffb347', '#ff6b4a'],
    segments: [
      { start: 14, end: 14.5, kind: 'busy' },
      { start: 14.5, end: 18, kind: 'free' },
      { start: 18, end: 18.5, kind: 'busy' },
      { start: 18.5, end: 22, kind: 'free' },
    ],
  },
];

const avatarStyle = (member: DemoMember): React.CSSProperties =>
  ({
    '--av-a': member.gradient[0],
    '--av-b': member.gradient[1],
  }) as React.CSSProperties;

export const ProductPreview: React.FC = () => {
  return (
    <section id="product" className="product">
      <div className="container">
        <p className="product__label">Product preview — illustrative data</p>

        <div className="product__panel">
          <div className="panel-head">
            <div>
              <p className="panel-eyebrow">Preview workspace</p>
              <h2 className="panel-title">
                Your group right now
                <span className="live-pill">
                  <span className="live-dot" />
                  Live preview
                </span>
              </h2>
            </div>
            <span className="panel-meta">4 members · Today</span>
          </div>

          <div className="panel-members" aria-label="Group member availability">
            {MEMBERS.map((member, index) => (
              <div
                key={member.name}
                className={`member ${member.free ? 'member--free' : 'member--busy'}`}
                style={{ ...avatarStyle(member), animationDelay: `${140 + index * 70}ms` }}
              >
                <span className="avatar">{member.initials}</span>
                <div className="member__info">
                  <div className="member__name">{member.name}</div>
                  <div className="member__status">
                    <span className="status-dot" />
                    <span>{member.status}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="next-window">
            <div className="next-window__avatars" aria-hidden="true">
              {MEMBERS.map((member) => (
                <span key={member.name} className="mini-avatar" style={avatarStyle(member)}>
                  {member.initials}
                </span>
              ))}
            </div>
            <div className="next-window__copy">
              <p className="next-window__label">Next time everyone's free</p>
              <p className="next-window__time">Today · 6:30 PM – 8:00 PM</p>
            </div>
            <span className="next-window__badge">1h 30m overlap</span>
          </div>

          <div className="timeline">
            <div className="timeline-head">
              <span className="timeline-title">Today's availability</span>
              <div className="timeline-legend">
                <span>
                  <span className="legend-dot legend-dot--free" />
                  Free
                </span>
                <span>
                  <span className="legend-dot legend-dot--busy" />
                  Busy
                </span>
              </div>
            </div>

            <div className="timeline-body">
              <div className="timeline-hours" aria-hidden="true">
                {HOUR_LABELS.map((label) => (
                  <span key={label}>{label}</span>
                ))}
              </div>

              <div className="timeline-lanes">
                {MEMBERS.map((member) => (
                  <div key={member.name} className="lane">
                    <span className="lane__label">
                      <span className="lane__avatar" style={avatarStyle(member)} aria-hidden="true">
                        {member.initials}
                      </span>
                      {member.name}
                    </span>
                    <div className="lane__track" aria-hidden="true">
                      {member.segments.map((segment, index) => (
                        <span
                          key={`${member.name}-${segment.start}`}
                          className={`segment segment--${segment.kind}`}
                          style={{
                            left: `${pct(segment.start)}%`,
                            width: `${pct(segment.end) - pct(segment.start)}%`,
                            animationDelay: `${320 + index * 80}ms`,
                          }}
                        />
                      ))}
                      <span
                        className="lane__window"
                        style={{
                          left: `${pct(SHARED_WINDOW.start)}%`,
                          width: `${pct(SHARED_WINDOW.end) - pct(SHARED_WINDOW.start)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="panel-foot">
            <span>Illustrative preview — not live user data.</span>
            <span className="panel-foot__mono">All times local</span>
          </div>
        </div>
      </div>
    </section>
  );
};
