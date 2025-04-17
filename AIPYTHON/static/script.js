// Loading indicator functionality
const loadingIndicator = document.querySelector('.loading-indicator');

function showLoading() {
  loadingIndicator.classList.remove('hidden');
}

function hideLoading() {
  loadingIndicator.classList.add('hidden');
  // Always add the loaded class to the body to ensure it's visible
  document.body.classList.add('loaded');
}

// Hide loading indicator when page is fully loaded
window.addEventListener('load', () => {
  hideLoading();
});

// Also hide loading indicator when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Hide loading indicator after a short delay to ensure everything is loaded
  setTimeout(hideLoading, 500);
});

document.addEventListener('DOMContentLoaded', () => {
    // Check if Anime.js is loaded
    if (typeof anime === 'undefined') {
        console.error('Anime.js failed to load. Using fallback animations.');
        // Add fallback class to enable CSS animations
        document.body.classList.add('anime-fallback');
    } else {
        console.log('Anime.js loaded successfully');
    }
    
    // DOM Elements
    const chatContainer = document.getElementById('chatContainer');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const chatForm = document.getElementById('chatForm');
    const charCount = document.getElementById('charCount');
    const errorMessage = document.getElementById('errorMessage');
    const themeToggle = document.getElementById('themeToggle');
    const plusButton = document.getElementById('plusButton');
    const imageOptions = document.getElementById('imageOptions');
    const uploadImage = document.getElementById('uploadImage');
    const takePhoto = document.getElementById('takePhoto');
    
    // Constants
    const MAX_CHARS = 500;
    
    // Animation variables
    let particles = [];
    
    // Initialize the application
    function init() {
        // Create background elements
        createBackgroundProps();
        createParticles();
        
        // Start animations
        startAnimations();
        
        // Initialize theme
        initTheme();
        
        // Add welcome message
        setTimeout(() => {
            addMessage("👋 Welcome to the Shopping AI Assistant! I can help you find the best products based on your needs. Try asking me something like:\n\n- Best wireless headphones under $200\n- Top-rated coffee makers for beginners\n- Affordable running shoes with good support\n- Best laptops for video editing under $1000", false);
        }, 1000);
        
        // Event Listeners
        userInput.addEventListener('input', updateCharCount);
        
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            sendMessage();
        });
        
        // Plus button for image options
        plusButton.addEventListener('click', (e) => {
            e.stopPropagation();
            const isExpanded = plusButton.getAttribute('aria-expanded') === 'true';
            plusButton.setAttribute('aria-expanded', !isExpanded);
            
            if (!isExpanded) {
                imageOptions.removeAttribute('hidden');
                imageOptions.classList.add('animate-in');
            } else {
                imageOptions.setAttribute('hidden', '');
                imageOptions.classList.remove('animate-in');
            }
        });
        
        // Close image options when clicking outside
        document.addEventListener('click', (e) => {
            if (!imageOptions.contains(e.target) && e.target !== plusButton) {
                plusButton.setAttribute('aria-expanded', 'false');
                imageOptions.setAttribute('hidden', '');
                imageOptions.classList.remove('animate-in');
            }
        });
        
        // Prevent clicks inside image options from closing it
        imageOptions.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        
        // Handle image upload
        uploadImage.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Upload image clicked');
            
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.onchange = async function(e) {
                const file = e.target.files[0];
                if (file) {
                    // Validate file size (max 5MB)
                    if (file.size > 5 * 1024 * 1024) {
                        showError('Image size should be less than 5MB');
                        return;
                    }
                    
                    // Validate file type
                    if (!file.type.startsWith('image/')) {
                        showError('Please upload an image file');
                        return;
                    }
                    
                    // Show loading state
                    addMessage("Processing your shopping list image...", false);
                    
                    try {
                        // Create FormData to send the image
                        const formData = new FormData();
                        formData.append('image', file);
                        
                        // Send image to server
                        const response = await fetch('/api/process-image', {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.error || 'Failed to process image');
                        }
                        
                        const data = await response.json();
                        
                        // Display the processed shopping list
                        if (data.items && data.items.length > 0) {
                            let message = "I've identified the following items in your shopping list:\n\n";
                            data.items.forEach(item => {
                                message += `• ${item}\n`;
                            });
                            message += "\nWould you like recommendations for any of these items?";
                            addMessage(message);
                        } else {
                            addMessage("I couldn't identify any items in the image. Please try taking a clearer photo or upload a different image.");
                        }
                        
                    } catch (error) {
                        console.error('Error processing image:', error);
                        showError(`Error: ${error.message}. Please try again.`);
                    }
                }
            };
            input.click();
            imageOptions.hidden = true;
            plusButton.setAttribute('aria-expanded', 'false');
        });
        
        // Handle photo capture
        takePhoto.addEventListener('click', (e) => {
            e.stopPropagation();
            // Check if the browser supports the MediaDevices API
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                navigator.mediaDevices.getUserMedia({ video: true })
                    .then(async (stream) => {
                        // Create video element to show camera feed
                        const video = document.createElement('video');
                        video.srcObject = stream;
                        video.autoplay = true;
                        
                        // Create canvas to capture image
                        const canvas = document.createElement('canvas');
                        const context = canvas.getContext('2d');
                        
                        // Wait for video to be ready
                        video.onloadedmetadata = async () => {
                            canvas.width = video.videoWidth;
                            canvas.height = video.videoHeight;
                            context.drawImage(video, 0, 0);
                            
                            // Convert canvas to blob
                            canvas.toBlob(async (blob) => {
                                // Stop the camera
                                stream.getTracks().forEach(track => track.stop());
                                
                                // Show loading state
                                addMessage("Processing your shopping list photo...", false);
                                
                                // Create FormData to send the image
                                const formData = new FormData();
                                formData.append('image', blob, 'photo.jpg');
                                
                                try {
                                    // Send image to server
                                    const response = await fetch('/api/process-image', {
                                        method: 'POST',
                                        body: formData
                                    });
                                    
                                    if (!response.ok) {
                                        throw new Error('Failed to process image');
                                    }
                                    
                                    const data = await response.json();
                                    
                                    if (data.error) {
                                        throw new Error(data.error);
                                    }
                                    
                                    // Display the processed shopping list
                                    if (data.items && data.items.length > 0) {
                                        let message = "I've identified the following items in your shopping list:\n\n";
                                        data.items.forEach(item => {
                                            message += `• ${item}\n`;
                                        });
                                        message += "\nWould you like recommendations for any of these items?";
                                        addMessage(message);
                                    } else {
                                        addMessage("I couldn't identify any items in the photo. Please try taking a clearer photo.");
                                    }
                                    
                                } catch (error) {
                                    console.error('Error processing image:', error);
                                    showError('Failed to process the photo. Please try again.');
                                }
                            }, 'image/jpeg');
                        };
                    })
                    .catch((error) => {
                        console.error('Error accessing camera:', error);
                        showError('Could not access camera. Please check permissions.');
                    });
            } else {
                showError('Camera access is not supported in this browser.');
            }
            imageOptions.hidden = true;
        });
    }
    
    // Create background particles
    function createParticles() {
        const container = document.querySelector('.container');
        const particleCount = 15;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;
            container.appendChild(particle);
            
            particles.push({
                element: particle,
                x: Math.random() * window.innerWidth,
                y: Math.random() * window.innerHeight,
                speedX: (Math.random() - 0.5) * 0.5,
                speedY: (Math.random() - 0.5) * 0.5,
                size: 5 + Math.random() * 10
            });
        }
    }
    
    // Animate particles with Anime.js
    function animateParticles() {
        particles.forEach(particle => {
            anime({
                targets: particle.element,
                translateX: [
                    { value: particle.x + 50, duration: 2000, easing: 'easeInOutQuad' },
                    { value: particle.x - 50, duration: 2000, easing: 'easeInOutQuad' }
                ],
                translateY: [
                    { value: particle.y + 50, duration: 2000, easing: 'easeInOutQuad' },
                    { value: particle.y - 50, duration: 2000, easing: 'easeInOutQuad' }
                ],
                scale: [
                    { value: 1.2, duration: 1000, easing: 'easeInOutQuad' },
                    { value: 1, duration: 1000, easing: 'easeInOutQuad' }
                ],
                opacity: [
                    { value: 0.8, duration: 1000, easing: 'easeInOutQuad' },
                    { value: 0.4, duration: 1000, easing: 'easeInOutQuad' }
                ],
                loop: true,
                direction: 'alternate',
                delay: Math.random() * 1000
            });
        });
    }
    
    // Create background props
    function createBackgroundProps() {
        const container = document.querySelector('.container');
        const propsContainer = document.createElement('div');
        propsContainer.className = 'background-props';
        
        // Create shopping-related props
        const props = [
            { icon: '🛍️', class: 'prop-shopping-bag', delay: 0 },
            { icon: '🏷️', class: 'prop-tag', delay: 200 },
            { icon: '🛒', class: 'prop-cart', delay: 400 },
            { icon: '🔍', class: 'prop-search', delay: 600 },
            { icon: '⭐', class: 'prop-star', delay: 800 }
        ];
        
        props.forEach(prop => {
            const propElement = document.createElement('div');
            propElement.className = `prop ${prop.class}`;
            propElement.textContent = prop.icon;
            
            // Position props randomly across the screen
            propElement.style.left = `${Math.random() * 80 + 10}%`;
            propElement.style.top = `${Math.random() * 80 + 10}%`;
            
            propsContainer.appendChild(propElement);
        });
        
        container.appendChild(propsContainer);
    }
    
    // Start animations with Anime.js
    function startAnimations() {
        // Animate particles
        animateParticles();
        
        // Animate UI elements with Anime.js
        anime({
            targets: '.header',
            opacity: [0, 1],
            translateY: [-20, 0],
            duration: 800,
            easing: 'easeOutExpo',
            delay: 100
        });
        
        anime({
            targets: '.input-area',
            opacity: [0, 1],
            translateY: [20, 0],
            duration: 800,
            easing: 'easeOutExpo',
            delay: 300
        });
        
        anime({
            targets: '.footer',
            opacity: [0, 1],
            translateY: [20, 0],
            duration: 800,
            easing: 'easeOutExpo',
            delay: 500
        });
        
        // Animate background props with more movement
        anime({
            targets: '.prop',
            translateY: [
                { value: -30, duration: 3000, easing: 'easeInOutQuad' },
                { value: 30, duration: 3000, easing: 'easeInOutQuad' }
            ],
            translateX: [
                { value: -20, duration: 4000, easing: 'easeInOutQuad' },
                { value: 20, duration: 4000, easing: 'easeInOutQuad' }
            ],
            rotate: [
                { value: 10, duration: 2000, easing: 'easeInOutQuad' },
                { value: -10, duration: 2000, easing: 'easeInOutQuad' }
            ],
            scale: [
                { value: 1.1, duration: 2000, easing: 'easeInOutQuad' },
                { value: 0.9, duration: 2000, easing: 'easeInOutQuad' }
            ],
            loop: true,
            direction: 'alternate',
            delay: anime.stagger(200)
        });
    }
    
    // Initialize theme
    function initTheme() {
        // Check for saved theme preference or use system preference
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
            document.body.classList.add('dark-mode');
            themeToggle.setAttribute('aria-pressed', 'true');
        }
        
        // Theme toggle event listener
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            themeToggle.setAttribute('aria-pressed', isDark);
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            
            // Animate theme toggle
            anime({
                targets: themeToggle,
                rotate: [0, 180],
                duration: 500,
                easing: 'easeInOutQuad'
            });
        });
    }
    
    // Update character count
    function updateCharCount() {
        const count = userInput.value.length;
        charCount.textContent = count;
        
        // Add warning class when approaching limit
        if (count > MAX_CHARS * 0.9) {
            charCount.parentElement.classList.add('warning');
        } else {
            charCount.parentElement.classList.remove('warning');
        }
        
        // Enable/disable send button
        sendButton.disabled = count === 0;
        
        // Add subtle animation to the input when typing
        if (count > 0) {
            userInput.classList.add('typing');
            document.body.classList.add('typing');
        } else {
            userInput.classList.remove('typing');
            document.body.classList.remove('typing');
        }
    }
    
    // Message handling with Anime.js animations
    function addMessage(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
        
        // Format line breaks, lists, and links
        const formattedText = text
            .replace(/\n/g, '<br>')
            .replace(/- /g, '• ')
            .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = isUser ? text : formattedText;
        
        messageDiv.appendChild(messageContent);
        chatContainer.appendChild(messageDiv);
        
        // Animate message with Anime.js
        anime({
            targets: messageDiv,
            opacity: [0, 1],
            translateY: [20, 0],
            duration: 500,
            easing: 'easeOutExpo',
            complete: () => {
                // Add highlight effect
                messageDiv.classList.add('highlight');
                setTimeout(() => {
                    messageDiv.classList.remove('highlight');
                }, 2000);
            }
        });
        
        // Smooth scroll to bottom
        anime({
            targets: chatContainer,
            scrollTop: chatContainer.scrollHeight,
            duration: 500,
            easing: 'easeOutExpo'
        });
    }
    
    // Show error message with Anime.js
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.hidden = false;
        
        // Animate error message
        anime({
            targets: errorMessage,
            opacity: [0, 1],
            translateY: [-10, 0],
            duration: 300,
            easing: 'easeOutExpo',
            complete: () => {
                // Hide after 5 seconds
                setTimeout(() => {
                    anime({
                        targets: errorMessage,
                        opacity: 0,
                        translateY: -10,
                        duration: 300,
                        easing: 'easeInExpo',
                        complete: () => {
                            errorMessage.hidden = true;
                        }
                    });
                }, 5000);
            }
        });
    }
    
    // API call with enhanced user experience
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Clear input and update UI
        userInput.value = '';
        updateCharCount();
        
        // Add user message with animation
        addMessage(message, true);
        
        try {
            // Animate send button
            anime({
                targets: sendButton,
                scale: [1, 0.95, 1],
                duration: 300,
                easing: 'easeInOutQuad'
            });
            
            sendButton.classList.add('sending');
            sendButton.setAttribute('aria-busy', 'true');
            sendButton.querySelector('.sr-only').textContent = 'Sending message...';
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: message })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                console.error('Server Error:', data);
                throw new Error(data.details || data.error || 'Failed to get response');
            }
            
            if (!data.response) {
                throw new Error('No recommendations found');
            }
            
            // Add AI response
            addMessage(data.response);
            
            // Reset button state
            sendButton.classList.remove('sending');
            sendButton.setAttribute('aria-busy', 'false');
            sendButton.querySelector('.sr-only').textContent = 'Loading...';
            
        } catch (error) {
            console.error('Error:', error);
            showError(error.message);
            
            // Reset button state
            sendButton.classList.remove('sending');
            sendButton.setAttribute('aria-busy', 'false');
            sendButton.querySelector('.sr-only').textContent = 'Loading...';
        }
    }
    
    // Initialize the application
    init();
});