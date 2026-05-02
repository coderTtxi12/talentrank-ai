/**
 * Top navigation bar component.
 */
import { Link } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { toggleSidebar } from '@/store/slices/uiSlice';
import { APP_NAME, NAV_CONTEXT_LINE } from '@/constants/branding';

const Navbar = () => {
  const dispatch = useAppDispatch();
  const { sidebarOpen } = useAppSelector((state) => state.ui);

  return (
    <nav className="bg-white border-b border-gray-200 fixed w-full z-30 top-0">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={() => dispatch(toggleSidebar())}
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-200"
              aria-label="Toggle sidebar"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                {sidebarOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>

            <Link to="/" className="flex flex-col ml-4">
              <span className="flex items-center">
                <span className="text-2xl mr-2" aria-hidden>
                  🛵
                </span>
                <span className="text-xl font-bold text-primary-600">{APP_NAME}</span>
              </span>
              <span className="hidden sm:block text-xs text-gray-500 mt-0.5 pl-9">
                {NAV_CONTEXT_LINE}
              </span>
            </Link>
          </div>

          <div className="hidden md:flex items-center gap-2 text-lg">
            <span title="España">🇪🇸</span>
            <span title="México">🇲🇽</span>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
