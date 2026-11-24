import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import JobRequestForm from '../../components/JobRequestForm';

export default function PostJob() {
  const location = useLocation();
  const navigate = useNavigate();
  const preset = location.state || {};

  return (
    <div className="max-w-2xl mx-auto p-6">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>
      <h1 className="text-3xl font-bold text-foreground">Post a Job</h1>
      <p className="text-muted-foreground mt-1">Tell us the details — we&apos;ll match you with the right pros.</p>
      <JobRequestForm preset={preset} />
    </div>
  );
}
