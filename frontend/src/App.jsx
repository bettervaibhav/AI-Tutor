import { Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import TutorRoom from "./pages/TutorRoom.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/study/:subjectId" element={<TutorRoom />} />
    </Routes>
  );
}
