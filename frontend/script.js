// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const optionButtons = document.getElementById('optionButtons');

// Backend API URL - handles both development and production
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/chat'
    : 'https://medicalbot-akmw.onrender.com';  // Replace with your actual Render backend URL

// User data state
let userData = {
    state: null
};

// Initialize the chat
function initChat() {
    // Add welcome message
    addBotMessage("Welcome to the Medical Appointment Booking System!");
    
    // Check if backend is available
    checkBackendConnection();
}

// Check if backend is available
async function checkBackendConnection() {
    try {
        // Add loading message
        const loadingMsg = "Connecting to server...";
        addBotMessage(loadingMsg);
        
        // First message to start the conversation
        await sendMessage("Hello");
        
        // Remove loading message if successful
        const messages = chatMessages.querySelectorAll('.bot-message');
        if (messages.length > 1 && messages[messages.length - 2].textContent === loadingMsg) {
            chatMessages.removeChild(messages[messages.length - 2]);
        }
    } catch (error) {
        // Show connection error
        addBotMessage("⚠️ Could not connect to the server. Please make sure the backend is running.");
    }
}

// Add a bot message to the chat
function addBotMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', 'bot-message');
    messageElement.textContent = message;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add a user message to the chat
function addUserMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', 'user-message');
    messageElement.textContent = message;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send message to backend
async function sendMessage(message) {
    try {
        // Add user message to UI
        if (message !== "Hello") {
            addUserMessage(message);
        }
        
        // Prepare request data
        const requestData = {
            message: message,
            user_data: userData
        };
        
        // Show typing indicator
        const typingIndicator = document.createElement('div');
        typingIndicator.classList.add('message', 'bot-message', 'typing-indicator');
        typingIndicator.textContent = "Typing...";
        chatMessages.appendChild(typingIndicator);
        
        // Call API
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData),
            // Add timeout
            signal: AbortSignal.timeout(10000) // 10 second timeout
        });
        
        // Remove typing indicator
        chatMessages.removeChild(typingIndicator);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Parse response
        const data = await response.json();
        
        // Update UI with bot response
        addBotMessage(data.response);
        
        // Update user data
        userData = data.data || {};
        
        // Handle different actions
        handleAction(data.action, data.data);
        
    } catch (error) {
        // Remove typing indicator if it exists
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            chatMessages.removeChild(typingIndicator);
        }
        
        console.error('Error sending message:', error);
        if (error.name === 'AbortError') {
            addBotMessage("The server is taking too long to respond. Please check if the backend is running properly.");
        } else if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
            addBotMessage("Cannot connect to the server. Please make sure the backend is running at http://localhost:8000");
        } else {
            addBotMessage("Sorry, there was an error processing your request.");
        }
    }
}

// Handle different response actions
function handleAction(action, data) {
    // Handle option buttons if provided in the response
    if (action === 'show_options' && data.options) {
        displayOptionButtons(data.options);
    } else {
        // Clear option buttons if no options provided
        optionButtons.innerHTML = '';
    }
}

// Display option buttons (departments, doctors, timings, yes/no)
function displayOptionButtons(options) {
    // Clear previous buttons
    optionButtons.innerHTML = '';
    
    if (Array.isArray(options)) {
        options.forEach(option => {
            const button = document.createElement('button');
            button.classList.add('option-button');
            button.textContent = option;
            
            // Add click event to send the selected option
            button.addEventListener('click', () => {
                // Highlight selected button
                const allButtons = optionButtons.querySelectorAll('.option-button');
                allButtons.forEach(btn => btn.classList.remove('selected'));
                button.classList.add('selected');
                
                // Send the selected option
                sendMessage(option);
                
                // Clear the buttons after selection
                setTimeout(() => {
                    optionButtons.innerHTML = '';
                }, 500);
            });
            
            optionButtons.appendChild(button);
        });
    }
}

// Event listeners
sendButton.addEventListener('click', () => {
    const message = userInput.value.trim();
    if (message) {
        sendMessage(message);
        userInput.value = '';
    }
});

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const message = userInput.value.trim();
        if (message) {
            sendMessage(message);
            userInput.value = '';
        }
    }
});

// Initialize the chat when the page loads
window.addEventListener('load', initChat); 