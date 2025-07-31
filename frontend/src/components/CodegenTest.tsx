import React, { useState } from 'react';
import { getCodegenService, CodegenAPIError } from '../services/codegen';

const CodegenTest: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string>('');
  const [error, setError] = useState<string>('');

  const testCodegenAPI = async () => {
    setLoading(true);
    setError('');
    setResult('');

    try {
      const codegenService = getCodegenService();
      
      // Test organization info
      const orgInfo = await codegenService.getOrganization();
      setResult(`✅ Organization: ${orgInfo.name || 'Unknown'} (ID: ${orgInfo.id})`);
      
    } catch (err) {
      if (err instanceof CodegenAPIError) {
        setError(`❌ Codegen API Error: ${err.message}`);
      } else {
        setError(`❌ Error: ${err}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const testAgentRun = async () => {
    setLoading(true);
    setError('');
    setResult('');

    try {
      const codegenService = getCodegenService();
      
      // Create a test agent run
      const agentRun = await codegenService.createAgentRun({
        target: 'Create a simple hello world function in Python',
        repo_name: 'Zeeeepa/CodegenCICD',
        auto_confirm_plans: true,
        max_iterations: 3,
      });
      
      setResult(`✅ Agent Run Created: ID ${agentRun.id}, Status: ${agentRun.status}, URL: ${agentRun.web_url}`);
      
    } catch (err) {
      if (err instanceof CodegenAPIError) {
        setError(`❌ Codegen API Error: ${err.message}`);
      } else {
        setError(`❌ Error: ${err}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">🧪 Codegen API Test</h3>
      
      <div className="space-y-4">
        <div className="flex space-x-4">
          <button
            onClick={testCodegenAPI}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? '⏳ Testing...' : '🏢 Test Organization'}
          </button>
          
          <button
            onClick={testAgentRun}
            disabled={loading}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            {loading ? '⏳ Creating...' : '🤖 Test Agent Run'}
          </button>
        </div>
        
        {result && (
          <div className="p-3 bg-green-50 border border-green-200 rounded">
            <p className="text-green-800">{result}</p>
          </div>
        )}
        
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded">
            <p className="text-red-800">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CodegenTest;
