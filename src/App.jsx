import React, { useState } from 'react';

function App() {
  const [travelRequest, setTravelRequest] = useState('');
  const [age, setAge] = useState(30);
  const [travelStyle, setTravelStyle] = useState(['Cultural Experience', 'Food']);
  const [budget, setBudget] = useState('Standard');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const travelStyles = [
    "Cultural Experience",
    "Nature",
    "Food",
    "Adventure",
    "Relaxation",
    "Shopping",
    "History"
  ];

  const handleTravelStyleChange = (style) => {
    setTravelStyle(prev => 
      prev.includes(style)
        ? prev.filter(s => s !== style)
        : [...prev, style]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!travelRequest.trim()) {
      alert('Please enter your travel request');
      return;
    }
    
    setIsLoading(true);
    
    // Add user message
    const userMessage = `${travelRequest}\n\n[Profile Information] Age: ${age}, Travel Style: ${travelStyle.join(', ')}, Budget: ${budget}`;
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    // Simulate AI response with different roles
    const roles = ['Travel Planner', 'Local Guide', 'Language Assistant', 'Currency Advisor'];
    
    for (const role of roles) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      setMessages(prev => [...prev, {
        role: 'assistant',
        agentRole: role,
        content: `This is a simulated response from the ${role}. In the final implementation, this will be replaced with actual AI responses.`
      }]);
    }
    
    setIsLoading(false);
  };

  const getMessageBackground = (message) => {
    if (message.role === 'user') return 'bg-blue-100';
    
    const backgrounds = {
      'Travel Planner': 'bg-green-100',
      'Local Guide': 'bg-yellow-100',
      'Language Assistant': 'bg-purple-100',
      'Currency Advisor': 'bg-cyan-100'
    };
    
    return backgrounds[message.agentRole] || 'bg-gray-100';
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-8">Travel Planner AI</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Input Form */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Travel Request</h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Describe your travel plans:
                </label>
                <textarea
                  value={travelRequest}
                  onChange={(e) => setTravelRequest(e.target.value)}
                  className="w-full h-32 p-2 border rounded"
                  placeholder="Example: I'm planning a one-week trip to Japan..."
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Age:
                </label>
                <input
                  type="number"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  className="w-full p-2 border rounded"
                  min="18"
                  max="100"
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Travel Style:
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {travelStyles.map(style => (
                    <label key={style} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={travelStyle.includes(style)}
                        onChange={() => handleTravelStyleChange(style)}
                        className="rounded text-blue-600"
                      />
                      <span className="text-sm">{style}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Budget Level:
                </label>
                <select
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="w-full p-2 border rounded"
                >
                  {['Budget', 'Affordable', 'Standard', 'Luxury', 'Ultra-Luxury'].map(level => (
                    <option key={level} value={level}>{level}</option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className={`w-full py-2 px-4 rounded text-white ${
                  isLoading 
                    ? 'bg-blue-400 cursor-not-allowed' 
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isLoading ? 'Generating Plan...' : 'Generate Travel Plan'}
              </button>
            </form>
          </div>

          {/* Chat Display */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Travel Plan Discussion</h2>
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`p-4 rounded ${getMessageBackground(message)}`}
                >
                  <div className="font-semibold mb-1">
                    {message.role === 'user' ? 'You' : message.agentRole}:
                  </div>
                  <div className="whitespace-pre-wrap">{message.content}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;