import type { ActorTimelineEvent } from "../../types/graph";

interface ActorTimelineProps {
  events: ActorTimelineEvent[];
}

export function ActorTimeline({ events }: ActorTimelineProps) {
  if (events.length === 0) {
    return (
      <section className="panel timeline-panel">
        <h2>Timeline</h2>
        <p className="empty-state">No mock lifecycle events are available for this actor.</p>
      </section>
    );
  }

  return (
    <section className="panel timeline-panel">
      <h2>Timeline</h2>
      <ol className="timeline-list">
        {events.map((event) => (
          <li className="timeline-item" key={event.id}>
            <div className="timeline-date">{event.date}</div>
            <div>
              <h3>{event.title}</h3>
              <p>{event.description}</p>
              <span className="confidence-pill">
                {Math.round(event.confidence * 100)}% confidence
              </span>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
