import React from 'react';
import QueryInput from '../components/QueryInput';
import AnswerDisplay from '../components/AnswerDisplay';
import SourceBadge from '../components/SourceBadge';
import DBStatusPanel from '../components/DBStatusPanel';

export default function Home() {
  return (
    <div className="home-page">
      <h1>EvoRAG</h1>
      <DBStatusPanel />
      <QueryInput />
      <AnswerDisplay />
      <SourceBadge />
    </div>
  );
}
