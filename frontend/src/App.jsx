import { useState } from "react";
import UploadScreen from "./components/UploadScreen";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [session, setSession] = useState(null); // { documentId, uploadResult, analysis }

  if (!session) {
    return <UploadScreen onReady={setSession} />;
  }

  return (
    <Dashboard
      documentId={session.documentId}
      uploadResult={session.uploadResult}
      analysis={session.analysis}
      onReset={() => setSession(null)}
    />
  );
}
