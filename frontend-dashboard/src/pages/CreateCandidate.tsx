/**
 * Alta de candidato (formulario).
 */
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAppDispatch } from '@/store/hooks';
import { createCandidate } from '@/store/slices/candidatesSlice';
import { addNotification } from '@/store/slices/uiSlice';
import { CandidateForm } from '@/components/candidates';
import type { CandidateCreateRequest } from '@/types/candidate';
import {
  CREATE_TITLE,
  CREATE_SUBTITLE,
  CREATE_BACK,
  CREATE_SUCCESS,
  CREATE_ERROR_FALLBACK,
} from '@/constants/branding';

interface ErrorInfo {
  message: string;
  errors?: string[];
}

const CreateCandidate = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const handleSubmit = async (data: CandidateCreateRequest) => {
    setLoading(true);
    setError(null);

    try {
      const result = await dispatch(createCandidate(data)).unwrap();

      dispatch(
        addNotification({
          type: 'success',
          message: CREATE_SUCCESS,
          duration: 5000,
        })
      );

      navigate(`/candidates/${result.id}`);
    } catch (err: unknown) {
      let errorInfo: ErrorInfo;

      if (typeof err === 'string') {
        errorInfo = { message: err };
      } else if (err && typeof err === 'object' && 'message' in err) {
        const e = err as { message: string; errors?: string[] };
        errorInfo = {
          message: e.message,
          errors: e.errors || [],
        };
      } else {
        errorInfo = { message: CREATE_ERROR_FALLBACK };
      }

      setError(errorInfo);

      dispatch(
        addNotification({
          type: 'error',
          message: errorInfo.message,
          duration: 5000,
        })
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <Link
            to="/candidates"
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            {CREATE_BACK}
          </Link>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">{CREATE_TITLE}</h1>
        <p className="text-gray-600">{CREATE_SUBTITLE}</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start gap-2">
            <span className="text-red-500">❌</span>
            <div className="flex-1">
              <p className="text-sm font-medium text-red-700">{error.message}</p>
              {error.errors && error.errors.length > 0 && (
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  {error.errors.map((errMsg, index) => (
                    <li key={index} className="text-sm text-red-600">
                      {errMsg}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      <CandidateForm onSubmit={handleSubmit} loading={loading} />
    </div>
  );
};

export default CreateCandidate;
