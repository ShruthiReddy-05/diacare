import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import HomePage from '../components/home/HomePage';

export default function Home() {
  return (
    <div className="page-container">
      <AppBar />
      <main className="page-content">
        <HomePage />
      </main>
      <BottomNav />
    </div>
  );
}
