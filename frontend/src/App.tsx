import { Navigate, Route, Routes } from "react-router-dom";
import { ActorPage } from "./pages/ActorPage";
import { GraphPage } from "./pages/GraphPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<GraphPage />} />
      <Route path="/actors/:actorId" element={<ActorPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
