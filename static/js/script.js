document.addEventListener("DOMContentLoaded", () => {
    const plantImageInput = document.getElementById("plantImage");
    const identificationResult = document.getElementById("identificationResult");
    const sendButton = document.getElementById("sendButton");
    const userMessageInput = document.getElementById("userMessage");
    const messagesContainer = document.getElementById("messages");
    const plantGreeting = document.getElementById("plantGreeting");
    const plantDetailsContainer = document.querySelector(".plant-details-container");
    let plantNameForChat = '';
    let isFirstBotMessage = true; // Flag to track if it's the initial bot message

    // Automatic identification on image upload
    if (plantImageInput) {
        plantImageInput.addEventListener("change", async () => {
            const file = plantImageInput.files[0];
            if (!file) {
                alert("Please upload a plant image.");
                return;
            }

            identificationResult.textContent = "Identifying plant...";
            identificationResult.style.opacity = "1";

            const formData = new FormData();
            formData.append("image", file);

            try {
                const response = await fetch("/identify_plant", {
                    method: "POST",
                    body: formData,
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }

                const data = await response.json();
                identificationResult.textContent = `Plant identified: ${data.identificationResult}`;
                plantNameForChat = data.identificationResult;

                // Store plant name for chatbot
                localStorage.setItem("plantName", data.identificationResult);
                window.location.href = '/chatbot';
            } catch (error) {
                console.error("Error:", error);
                alert("An error occurred while identifying the plant. Please try again.");
            }
        });
    }

    // Initialize chatbot with plant name from localStorage
    plantNameForChat = localStorage.getItem("plantName") || "the plant";
    if (plantGreeting) {
        plantGreeting.textContent = `You are chatting about: ${plantNameForChat}`;
    }

    // Trigger initial bot message
    fetch("/chatbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            email: "user@example.com",
            message: "",  // Empty message to trigger the default response in Flask
            plantName: plantNameForChat
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                displayBotMessage(data.message);
            } else {
                console.error('Failed to get initial bot message');
            }
        })
        .catch(error => console.error('Error:', error));

    // Event listeners for send button and Enter key
    if (sendButton) {
        sendButton.addEventListener("click", () => sendMessage());
    }
    userMessageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") sendMessage();
    });

    // Function to handle sending messages
    async function sendMessage() {
        const userMessage = userMessageInput.value.trim();
        if (!userMessage) return;

        addMessage(userMessage, "user");
        userMessageInput.value = "";

        try {
            const response = await fetch("/chatbot", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email: "user@example.com",
                    message: userMessage,
                    plantName: plantNameForChat
                })
            });
            const data = await response.json();

            if (response.ok) {
                displayBotMessage(data.message);
            } else {
                displayBotMessage("Error from chatbot");
            }
        } catch (error) {
            console.error("Error:", error);
            displayBotMessage("Server error");
        }
    }

    // Function to add user messages to the chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");
        messageDiv.textContent = text;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Function to display bot messages
    function displayBotMessage(chatbotMessage) {
        const botMessageDiv = document.createElement('div');
        botMessageDiv.classList.add('bot-message');

        // Format message with HTML
        const formattedMessage = chatbotMessage
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold headings
            .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italics for subheadings
            .replace(/\n/g, "<br>"); // Replace new lines with breaks

        // Insert formatted HTML


        if (isFirstBotMessage) {
            // Display the first bot message in the plant details container
            plantDetailsContainer.innerHTML = formattedMessage;
            isFirstBotMessage = false; // Set flag to false after displaying initial message
        } else {
            // Append future bot messages to the messages container
            botMessageDiv.innerHTML = formattedMessage;
            messagesContainer.appendChild(botMessageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
});
