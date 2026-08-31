import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getActorTimeline } from "../api/graph";
import { ActorTimeline } from "../components/actor/ActorTimeline";
import type { ActorTimelineEvent } from "../types/graph";

export function ActorPage() {
  const { actorId = "" } = useParams();
  const [events, setEvents] = useState<ActorTimelineEvent[]>([]);

  useEffect(() => {
    let isMounted = true;

    getActorTimeline(actorId).then((timelineEvents) => {
      if (isMounted) {
        setEvents(timelineEvents);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [actorId]);

  return (
    <main className="page-shell actor-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Actor Detail</p>
          <h1>{actorId || "Unknown actor"}</h1>
        </div>
        <Link className="text-button" to="/">
          Back to graph
        </Link>
      </header>
      <ActorTimeline events={events} />
    </main>
  );
}
