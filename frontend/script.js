// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const optionButtons = document.getElementById('optionButtons');

// Backend API URL - handles both development and production
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/chat'
    : 'https://medicalbot-akmw.onrender.com/chat';  // Replace with your actual Render backend URL

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

// Add options directly to the chat flow
function addOptionsToChat(options) {
    const optionsContainer = document.createElement('div');
    optionsContainer.classList.add('in-chat-options');
    
    options.forEach(option => {
        const button = document.createElement('button');
        button.classList.add('chat-option-button');
        button.textContent = option.text || option;
        
        // Add click event to send the selected option
        button.addEventListener('click', () => {
            // Highlight selected button
            const allButtons = optionsContainer.querySelectorAll('.chat-option-button');
            allButtons.forEach(btn => btn.classList.remove('selected'));
            button.classList.add('selected');
            
            // Send the selected option
            const value = option.value || option;
            sendMessage(value);
        });
        
        optionsContainer.appendChild(button);
    });
    
    chatMessages.appendChild(optionsContainer);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send message to backend
async function sendMessage(message) {
    try {
        // Add user message to UI
        if (message !== "Hello") {
            addUserMessage(message);
        }
        
        // Disable all option buttons to prevent multiple clicks
        const buttons = document.querySelectorAll('.chat-option-button');
        buttons.forEach(button => {
            button.disabled = true;
            button.style.opacity = '0.5';
            button.style.cursor = 'not-allowed';
        });
        
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
    // Debug logging
    console.log("Action received:", action);
    console.log("Data received:", data);
    
    // Check for specific actions that need buttons
    if (action === 'offer_booking') {
        // Display Yes/No buttons in chat
        addOptionsToChat([
            { text: "Yes", value: "Yes" },
            { text: "No", value: "No" }
        ]);
    } else if (action === 'show_existing_appointment') {
        // Display cancel and new appointment buttons in chat
        addOptionsToChat([
            { text: "Cancel Appointment", value: "cancel" },
            { text: "Book New Appointment", value: "book new appointment" }
        ]);
    } else if (action === 'confirm_cancellation') {
        // Display cancellation confirmation buttons in chat
        addOptionsToChat([
            { text: "Yes, Cancel", value: "yes" },
            { text: "No, Keep", value: "no" }
        ]);
    } else if (action === 'show_options' && data && data.options) {
        // Generic option buttons handler - add to chat
        console.log("Showing options:", data.options);
        addOptionsToChat(data.options);
    } else if (action === 'request_department') {
        // Fallback for backward compatibility
        const departments = ["Cardiology", "Neurology", "General Physician"];
        addOptionsToChat(departments);
    } else if (action === 'request_doctor') {
        // Fallback for backward compatibility
        if (data && data.doctors && Array.isArray(data.doctors)) {
            addOptionsToChat(data.doctors);
        } else {
            const errorMsg = document.createElement('div');
            errorMsg.className = 'error';
            errorMsg.textContent = 'Error: No department specified. Please type your selection.';
            chatMessages.appendChild(errorMsg);
        }
    } else if (action === 'request_date' && data && data.available_dates) {
        // Fallback for backward compatibility
        addOptionsToChat(data.available_dates);
    } else if (action === 'request_time' && data && data.available_slots) {
        // Fallback for backward compatibility
        addOptionsToChat(data.available_slots);
    } else if (action === 'show_appointments') {
        // Also handle show_appointments action for existing appointments
        addOptionsToChat([
            { text: "Cancel Appointment", value: "cancel" },
            { text: "Book New Appointment", value: "book new appointment" }
        ]);
    } else if (action === 'conversation_end') {
        // Disable input when conversation ends
        userInput.disabled = true;
        sendButton.disabled = true;
        
        // Add a restart button to chat
        const restartOptions = [{ text: "Start New Conversation", value: "Hello" }];
        addOptionsToChat(restartOptions);
        
        // Add event listener for the restart button
        const restartButtons = document.querySelectorAll('.chat-option-button');
        if (restartButtons.length > 0) {
            const restartButton = restartButtons[restartButtons.length - 1];
            restartButton.addEventListener('click', () => {
                userData = { state: null };
                userInput.disabled = false;
                sendButton.disabled = false;
            });
        }
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