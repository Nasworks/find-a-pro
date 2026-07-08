import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import './App.css';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { CartProvider } from './context/CartContext';
import { ViewModeProvider } from './context/ViewModeContext';
import { Toaster } from './components/ui/sonner';

import LandingRoleSelect from './pages/LandingRoleSelect';
import Login from './pages/Login';
import Signup from './pages/Signup';
import AuthCallback from './pages/AuthCallback';
import MainLayout from './components/layout/MainLayout';

import ClientHome from './pages/client/ClientHome';
import PostJob from './pages/client/PostJob';
import MyJobPosts from './pages/client/MyJobPosts';
import Bookings from './pages/client/Bookings';
import Messages from './pages/client/Messages';
import Marketplace from './pages/client/Marketplace';
import ProductDetail from './pages/client/ProductDetail';
import Cart from './pages/client/Cart';
import NewsFeed from './pages/client/NewsFeed';
import Profile from './pages/client/Profile';
import LiveMap from './pages/client/LiveMap';
import JobDetail from './pages/client/JobDetail';

import ProviderDashboard from './pages/provider/ProviderDashboard';
import ProviderJobBoard from './pages/provider/ProviderJobBoard';
import ProviderEarnings from './pages/provider/ProviderEarnings';
import ProviderCalendar from './pages/provider/ProviderCalendar';
import ProviderTradeStore from './pages/provider/ProviderTradeStore';
import Quotations from './pages/provider/Quotations';
import Team from './pages/provider/Team';
import TradesBoard from './pages/provider/TradesBoard';
import ExternalJobs from './pages/provider/ExternalJobs';
import TrackWorkers from './pages/provider/TrackWorkers';
import GpsDevices from './pages/provider/GpsDevices';
import JobHistory from './pages/provider/JobHistory';
import Referrals from './pages/provider/Referrals';
import Membership from './pages/provider/Membership';
import WarrantyClaims from './pages/provider/WarrantyClaims';

import PropertyDashboard from './pages/property/PropertyDashboard';
import InsuranceDashboard from './pages/insurance/InsuranceDashboard';
import LandlordDashboard from './pages/landlord/LandlordDashboard';
import FacilitiesDashboard from './pages/facilities/FacilitiesDashboard';
import Verification from './pages/provider/Verification';
import ProfileContact from './pages/provider/ProfileContact';
import CostEstimator from './pages/shared/CostEstimator';
import GuideHelp from './pages/shared/GuideHelp';
import CommunityForum from './pages/shared/CommunityForum';
import ForumPostDetail from './pages/shared/ForumPostDetail';
import Tenancies from './pages/shared/Tenancies';
import ApprovalQueue from './pages/shared/ApprovalQueue';
import FindProviders from './pages/shared/FindProviders';
import ProviderProfile from './pages/shared/ProviderProfile';
import LegalPrivacy from './pages/shared/LegalPrivacy';
import ReportProvider from './pages/shared/ReportProvider';
import MyDisputes from './pages/shared/MyDisputes';
import MoreMenu from './pages/shared/MoreMenu';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading...</div>;
  if (!user) return <Navigate to="/" replace />;
  return children;
}

function RootRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading...</div>;
  if (user) {
    if (user.role === 'provider') return <Navigate to="/provider/dashboard" replace />;
    if (user.role === 'property') return <Navigate to="/property/dashboard" replace />;
    if (user.role === 'landlord') return <Navigate to="/landlord/dashboard" replace />;
    if (user.role === 'facilities') return <Navigate to="/facilities/dashboard" replace />;
    if (user.role === 'insurance') return <Navigate to="/insurance/dashboard" replace />;
    return <Navigate to="/client-home" replace />;
  }
  return <LandingRoleSelect />;
}

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<RootRoute />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        {/* Client routes */}
        <Route path="/client-home" element={<ClientHome />} />
        <Route path="/post-job" element={<PostJob />} />
        <Route path="/my-job-posts" element={<MyJobPosts />} />
        <Route path="/jobs/:jobId" element={<JobDetail />} />
        <Route path="/bookings" element={<Bookings />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/marketplace" element={<Marketplace />} />
        <Route path="/marketplace/product/:id" element={<ProductDetail />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/news-feed" element={<NewsFeed />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/live-map" element={<LiveMap />} />

        {/* Provider */}
        <Route path="/provider/dashboard" element={<ProviderDashboard />} />
        <Route path="/provider/job-board" element={<ProviderJobBoard />} />
        <Route path="/provider/earnings" element={<ProviderEarnings />} />
        <Route path="/provider/calendar" element={<ProviderCalendar />} />
        <Route path="/provider/trade-store" element={<ProviderTradeStore />} />
        <Route path="/provider/quotations" element={<Quotations />} />
        <Route path="/provider/team" element={<Team />} />
        <Route path="/provider/trades-board" element={<TradesBoard />} />
        <Route path="/provider/external-jobs" element={<ExternalJobs />} />
        <Route path="/provider/track-workers" element={<TrackWorkers />} />
        <Route path="/provider/gps-devices" element={<GpsDevices />} />
        <Route path="/provider/job-history" element={<JobHistory />} />
        <Route path="/provider/referrals" element={<Referrals />} />
        <Route path="/provider/membership" element={<Membership />} />
        <Route path="/provider/warranty-claims" element={<WarrantyClaims />} />

        {/* Property */}
        <Route path="/property/dashboard" element={<PropertyDashboard />} />

        {/* Landlord */}
        <Route path="/landlord/dashboard" element={<LandlordDashboard />} />

        {/* Facilities */}
        <Route path="/facilities/dashboard" element={<FacilitiesDashboard />} />

        {/* Insurance */}
        <Route path="/insurance/dashboard" element={<InsuranceDashboard />} />

        {/* Provider extras */}
        <Route path="/provider/verification" element={<Verification />} />
        <Route path="/provider/profile-contact" element={<ProfileContact />} />

        {/* Shared / all roles */}
        <Route path="/more" element={<MoreMenu />} />
        <Route path="/cost-estimator" element={<CostEstimator />} />
        <Route path="/guide-help" element={<GuideHelp />} />
        <Route path="/community-forum" element={<CommunityForum />} />
        <Route path="/community-forum/:postId" element={<ForumPostDetail />} />
        <Route path="/tenancies" element={<Tenancies />} />
        <Route path="/approvals" element={<ApprovalQueue />} />
        <Route path="/find-providers" element={<FindProviders />} />
        <Route path="/providers/:providerId" element={<ProviderProfile />} />
        <Route path="/legal-privacy" element={<LegalPrivacy />} />
        <Route path="/report-provider" element={<ReportProvider />} />
        <Route path="/my-disputes" element={<MyDisputes />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <ViewModeProvider>
        <AuthProvider>
          <CartProvider>
            <div className="App">
              <BrowserRouter>
                <AppRouter />
                <Toaster position="top-right" richColors />
              </BrowserRouter>
            </div>
          </CartProvider>
        </AuthProvider>
      </ViewModeProvider>
    </ThemeProvider>
  );
}

export default App;
