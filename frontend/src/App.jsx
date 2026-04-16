import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import DbtPipelines from './pages/DbtPipelines'
import Snowflake from './pages/Snowflake'
import Anomalies from './pages/Anomalies'
import Insights from './pages/Insights'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="dbt" element={<DbtPipelines />} />
        <Route path="snowflake" element={<Snowflake />} />
        <Route path="anomalies" element={<Anomalies />} />
        <Route path="insights" element={<Insights />} />
      </Route>
    </Routes>
  )
}
