import { mockGraph, mockTimelineEvents } from "../data/mockGraph";
import type { ActorTimelineEvent, GraphPayload } from "../types/graph";

export async function getGraphPayload(): Promise<GraphPayload> {
  return mockGraph;
}

export async function getActorTimeline(actorId: string): Promise<ActorTimelineEvent[]> {
  return mockTimelineEvents.filter((event) => event.actorId === actorId);
}
