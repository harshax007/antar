import dynamic from 'next/dynamic';

const PredictScreen = dynamic(() => import('./PredictScreen'), { ssr: false });

export default function PredictPage() {
  return <PredictScreen />;
}
