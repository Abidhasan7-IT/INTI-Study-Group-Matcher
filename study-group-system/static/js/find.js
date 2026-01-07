// Run when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Load subjects and goals dynamically
    loadSubjects();
    loadGoals();
    
    // Load groups from backend and display them (this will handle auth)
    loadAndDisplayGroups();
    
    // Generate AI recommendations when page loads
    generateAIRecommendations();

    // Add click event to the "Apply Filters" button
    const filterBtn = document.getElementById('filterBtn');
    
    // Remove any existing event listeners to prevent duplicates
    const newFilterBtn = filterBtn.cloneNode(true);
    filterBtn.parentNode.replaceChild(newFilterBtn, filterBtn);
    
    newFilterBtn.addEventListener('click', function(e) {
        e.preventDefault(); // Prevent any default form submission
        loadAndDisplayGroups(); // Refresh groups with filters
        generateAIRecommendations(); // Trigger AI recommendations
    });
});

function loadSubjects() {
    fetch('/api/subjects')
        .then(response => response.json())
        .then(data => {
            const subjectSelect = document.getElementById('filterSubject');
            // Keep the 'All Subjects' option
            subjectSelect.innerHTML = '<option value="all">All Subjects</option>';
            
            data.forEach(subject => {
                const option = document.createElement('option');
                option.value = subject.subject;
                option.textContent = formatSubjectName(subject.subject);
                subjectSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading subjects:', error);
        });
}

function loadGoals() {
    fetch('/api/goals')
        .then(response => response.json())
        .then(data => {
            const goalSelect = document.getElementById('filterGoal');
            // Keep the 'All Goals' option
            goalSelect.innerHTML = '<option value="all">All Goals</option>';
            
            data.forEach(goal => {
                const option = document.createElement('option');
                option.value = goal.goal;
                option.textContent = formatGoalName(goal.goal);
                goalSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading goals:', error);
        });
}

// Helper function to format subject names
function formatSubjectName(subjectCode) {
    const subjectMap = {
        'math101': 'Math 101',
        'prog101': 'Programming Fundamentals',
        'bus101': 'Business Ethics',
        'stats101': 'Statistics 101',
        'eng101': 'English Literature',
        'phy101': 'Physics 101',
        'chem101': 'Chemistry 101',
        'bio101': 'Biology 101',
        'eco101': 'Economics 101',
        'acc101': 'Accounting 101'
    };
    return subjectMap[subjectCode] || subjectCode.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
}

// Helper function to format goal names
function formatGoalName(goalCode) {
    const goalMap = {
        'midterm': 'Midterm Review',
        'homework': 'Homework Help',
        'project': 'Project Discussion',
        'final': 'Final Exam Prep',
        'assignment': 'Assignment Help',
        'presentation': 'Presentation Practice',
        'study': 'General Study Session'
    };
    return goalMap[goalCode] || goalCode.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
}

// Function to load groups and apply filters from backend
function loadAndDisplayGroups() {
    // Get filter values from the dropdowns
    const filterSubject = document.getElementById('filterSubject').value;
    const filterDate = document.getElementById('filterDate').value;
    const filterGoal = document.getElementById('filterGoal').value;

    // Build query parameters
    const params = new URLSearchParams(); 
    if (filterSubject && filterSubject !== 'all') {
        params.append('subject', filterSubject);
    }
    if (filterGoal && filterGoal !== 'all') {
        params.append('goal', filterGoal);
    }
    if (filterDate && filterDate !== 'all') {
        params.append('date', filterDate);
    }

    // Show loading indicator
    const groupsList = document.getElementById('groupsList');
    groupsList.innerHTML = '<p>Loading groups...</p>';

    // Fetch groups from backend - use POST to avoid potential redirect issues with GET
    fetch(`/find-group?${params}&format=json`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        }
    })
        .then(async response => {
            if (!response.ok) {
                if (response.status === 401) {
                    // Redirect to login if not authenticated
                    window.location.href = '/login';
                    return null;
                }
                throw new Error('Network response was not ok');
            }
            
            // Check if the response is JSON by examining the content type
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                // If not JSON, it might be a redirect response that returns HTML
                // Attempt to parse as JSON might fail, so check if we got redirected
                const responseText = await response.text();
                
                // If it looks like HTML, redirect to login
                if (responseText.startsWith('<!DOCTYPE') || responseText.startsWith('<html')) {
                    window.location.href = '/login';
                    return null;
                }
                
                // If it's actual JSON as text, parse it
                return JSON.parse(responseText);
            }
        })
        .then(groups => {
            if (groups === null) {
                // Authentication failure already handled by redirecting
                return;
            }
            // Display the groups
            displayGroups(groups);
        })
        .catch(error => {
            console.error('Error fetching groups:', error);
            // Check if this is a JSON parsing error caused by HTML response
            if (error instanceof SyntaxError && error.message.includes('Unexpected token')) {
                // Likely received HTML when expecting JSON - redirect to login
                window.location.href = '/login';
            } else {
                const groupsList = document.getElementById('groupsList');
                groupsList.innerHTML = '<p>Error loading groups. Please try again later.</p>';
            }
        });
}

// Helper function: Check if a group's date is in the selected range (thisWeek/nextWeek)
function isDateInRange(groupDate, range) {
    const today = new Date();
    const groupDateObj = new Date(groupDate);
    const startOfWeek = new Date(today.setDate(today.getDate() - today.getDay()));
    const endOfThisWeek = new Date(startOfWeek);
    endOfThisWeek.setDate(endOfThisWeek.getDate() + 6);
    const startOfNextWeek = new Date(endOfThisWeek);
    startOfNextWeek.setDate(startOfNextWeek.getDate() + 1);
    const endOfNextWeek = new Date(startOfNextWeek);
    endOfNextWeek.setDate(endOfNextWeek.getDate() + 6);

    if (range === 'thisWeek') {
        return groupDateObj >= startOfWeek && groupDateObj <= endOfThisWeek;
    } else if (range === 'nextWeek') {
        return groupDateObj >= startOfNextWeek && groupDateObj <= endOfNextWeek;
    }
    return true; // Default to true if range is "all"
}

// Function to display groups on the page (YOUR EXISTING CODE)
function displayGroups(groups) {
    const groupsList = document.getElementById('groupsList');

    // Ensure we completely clear the content before adding new content
    groupsList.innerHTML = '';
    
    // Additional safety: remove all child nodes to ensure complete clearing
    while (groupsList.firstChild) {
        groupsList.removeChild(groupsList.firstChild);
    }

    // If no groups found, show message
    if (groups.length === 0) {
        groupsList.innerHTML = '<p>No groups found. Try adjusting your filters or create a new group!</p>';
        return;
    }

    // Create a container for the group cards to apply grid layout
    const groupsContainer = document.createElement('div');
    groupsContainer.className = 'groups-container';

    // Loop through groups and create a card for each
    groups.forEach(group => {
        const groupCard = document.createElement('div');
        groupCard.className = 'group-card';

        // Convert subject code to friendly name (e.g., "math101" → "Math 101")
        const subjectName = getFriendlySubjectName(group.subject);
        // Convert goal code to friendly name (e.g., "midterm" → "Midterm Review")
        const goalName = getFriendlyGoalName(group.goal);

        // Use the backend's group ID format (group.id) for the data attribute
        // but display the group_id field
        const displayGroupId = group.id;

        // Check if group is full
        const isGroupFull = group.current_members >= group.max_members;
        const joinButtonClass = isGroupFull ? 'btn join-btn disabled' : 'btn join-btn';
        const joinButtonText = isGroupFull ? 'Group Full' : 'Join This Group';
        const joinButtonDisabled = isGroupFull ? 'disabled' : '';
        
        // Add group details to the card
        groupCard.innerHTML = `
            <h3>${subjectName} | ${goalName}</h3>
            <p><strong>Group ID:</strong> ${displayGroupId}</p>
            <p><strong>Date:</strong> ${formatDate(group.date)}</p>
            <p><strong>Time:</strong> ${group.time}</p>
            <p><strong>Location:</strong> ${group.location}</p>
            <p><strong>Members:</strong> ${group.current_members}/${group.max_members}</p>
            <button class="${joinButtonClass}" data-groupid="${group.id}" ${joinButtonDisabled}>${joinButtonText}</button>
        `;

        // Add the card to the groups container
        groupsContainer.appendChild(groupCard);
    });

    // Add the container to the groups list
    groupsList.appendChild(groupsContainer);

    // Add click events to all "Join This Group" buttons
    addJoinButtonEvents();
}

// Helper function: Convert subject code to friendly name
function getFriendlySubjectName(subjectCode) {
    return formatSubjectName(subjectCode);
}

// Helper function: Convert goal code to friendly name
function getFriendlyGoalName(goalCode) {
    return formatGoalName(goalCode);
}

// Helper function: Format date (YYYY-MM-DD → MM/DD/YYYY or DD/MM/YYYY)
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString(); // Uses your browser's default format
}

// Function to add click events to "Join" buttons
function addJoinButtonEvents() {
    const joinButtons = document.querySelectorAll('.join-btn:not(.disabled)');
    joinButtons.forEach(button => {
        button.addEventListener('click', function() {
            const groupId = this.getAttribute('data-groupid');
            joinGroup(groupId);
        });
    });
}

// Function to handle joining a group (YOUR EXISTING CODE)
function joinGroup(groupId) {
    // Try to join the group directly, handle auth errors appropriately
    joinGroupBackend(null, groupId); // Pass null for userId, backend will get it from session
}

// Helper function to join group via backend API
function joinGroupBackend(userId, groupId) {
    fetch(`/join-group/${groupId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        // Don't send user_id in body, let backend get it from session
        body: JSON.stringify({})
    })
    .then(async response => {
        if (!response.ok) {
            if (response.status === 401) {
                // Redirect to login if not authenticated
                window.location.href = '/login';
                return { error: 'Not authenticated' };
            }
            throw new Error('Network response was not ok');
        }
        
        // Check if the response is JSON by examining the content type
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            // If not JSON, it might be a redirect response that returns HTML
            const responseText = await response.text();
            
            // If it looks like HTML, redirect to login
            if (responseText.startsWith('<!DOCTYPE') || responseText.startsWith('<html')) {
                window.location.href = '/login';
                return { error: 'Not authenticated' };
            }
            
            // If it's actual JSON as text, parse it
            return JSON.parse(responseText);
        }
    })
    .then(data => {
        if (data && data.error) {
            alert(`Error joining group: ${data.error}`);
        } else {
            alert(`Success! You joined Group ${groupId}`);
            loadAndDisplayGroups();
            generateAIRecommendations(); // Refresh AI recommendations after joining
        }
    })
    .catch(error => {
        console.error('Error joining group:', error);
        // Check if this is a JSON parsing error caused by HTML response
        if (error instanceof SyntaxError && error.message.includes('Unexpected token')) {
            // Likely received HTML when expecting JSON - redirect to login
            window.location.href = '/login';
        } else {
            alert('An error occurred while joining the group');
        }
    });
}

// --------------------------
// AI RECOMMENDATION FEATURE
// --------------------------

// New function to trigger AI recommendations (called when filter button is clicked)
function generateAIRecommendations() {
    // Fetch AI recommendations from backend
    fetch('/auto-match', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(async response => {
        if (!response.ok) {
            if (response.status === 401) {
                // If unauthorized, don't show error, just don't display recommendations
                const recommendationList = document.getElementById('recommendation-list');
                recommendationList.innerHTML = '<p>Please join a group or create an account to receive personalized recommendations!</p>';
                return [];
            }
            throw new Error('Network response was not ok');
        }
        
        // Check if the response is JSON by examining the content type
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            // If not JSON, it might be a redirect response that returns HTML
            const responseText = await response.text();
            
            // If it looks like HTML, likely redirected due to auth issues
            if (responseText.startsWith('<!DOCTYPE') || responseText.startsWith('<html')) {
                const recommendationList = document.getElementById('recommendation-list');
                recommendationList.innerHTML = '<p>Please join a group or create an account to receive personalized recommendations!</p>';
                return [];
            }
            
            // If it's actual JSON as text, parse it
            return JSON.parse(responseText);
        }
    })
    .then(data => {
        if (data && data.matched_groups) {
            // Use the properly formatted recommendations from backend
            displayAIRecommendations(data.matched_groups);
        } else {
            // If no matched_groups in response, show empty recommendations
            displayAIRecommendations([]);
        }
    })
    .catch(error => {
        console.error('Error fetching recommendations:', error);
        // Check if this is a JSON parsing error caused by HTML response
        if (error instanceof SyntaxError && error.message.includes('Unexpected token')) {
            // Likely received HTML when expecting JSON - show appropriate message
            const recommendationList = document.getElementById('recommendation-list');
            recommendationList.innerHTML = '<p>Please join a group or create an account to receive personalized recommendations!</p>';
        } else {
            displayAIRecommendations([]);
        }
    });
}

// AI Logic: Score groups based on user filters (matches your group data structure)
function getAIRecommendations(userFilters, allGroups) {
    if (!allGroups || allGroups.length === 0) return [];

    // Score each group based on filter matches (higher = better match)
    const scoredGroups = allGroups.map(group => {
        let matchScore = 0;

        // 1. Subject match (5 points) - skip if "all"
        if (userFilters.subject !== 'all' && group.subject === userFilters.subject) {
            matchScore += 5;
        }

        // 2. Goal match (3 points) - skip if "all"
        if (userFilters.goal !== 'all' && group.goal === userFilters.goal) {
            matchScore += 3;
        }

        // 3. Date range match (2 points) - skip if "all"
        if (userFilters.date !== 'all' && isDateInRange(group.date, userFilters.date)) {
            matchScore += 2;
        }

        // 4. Group not full (1 point)
        if (group.current_members < group.max_members) {
            matchScore += 1;
        }

        return { ...group, matchScore };
    });

    // Return top 2 groups with highest scores
    return scoredGroups
        .sort((a, b) => b.matchScore - a.matchScore)
        .slice(0, 2);
}

// Display AI recommendations on the page (user-friendly format)
function displayAIRecommendations(recommendations) {
    const recommendationList = document.getElementById('recommendation-list');

    if (recommendations.length === 0) {
        recommendationList.innerHTML = "<p>No recommendations available. Try adjusting your filters or create a group!</p>";
        return;
    }

    // Create a container for the recommendation cards to apply grid layout
    const recommendationsContainer = document.createElement('div');
    recommendationsContainer.className = 'groups-container';
    
    recommendations.forEach(group => {
        // Use your existing helper functions for friendly names
        const subjectName = getFriendlySubjectName(group.subject);
        const goalName = getFriendlyGoalName(group.goal);
        
        const groupCard = document.createElement('div');
        groupCard.className = 'group-card';
        
        // Check if group is full
        const isGroupFull = group.current_members >= group.max_members;
        const joinButtonClass = isGroupFull ? 'btn disabled' : 'btn';
        const joinButtonText = isGroupFull ? 'Group Full' : 'Join Group';
        const joinButtonDisabled = isGroupFull ? 'disabled' : '';
        
        let buttonHtml;
        if (isGroupFull) {
            buttonHtml = `<button class="${joinButtonClass}" disabled>${joinButtonText}</button>`;
        } else {
            buttonHtml = `<button class="${joinButtonClass}" onclick="joinGroup('${group.id}'); return false;">${joinButtonText}</button>`;
        }
        
        groupCard.innerHTML = `
            <h3>${subjectName} (AI Recommended)</h3>
            <p><strong>Goal:</strong> ${goalName}</p>
            <p><strong>Date:</strong> ${formatDate(group.date)}</p>
            <p><strong>Time:</strong> ${group.time}</p>
            <p><strong>Location:</strong> ${group.location}</p>
            <p><strong>Members:</strong> ${group.current_members}/${group.max_members}</p>
            ${buttonHtml}
        `;
        
        recommendationsContainer.appendChild(groupCard);
    });
    
    // Clear the recommendation list and add the container
    recommendationList.innerHTML = "";
    recommendationList.appendChild(recommendationsContainer);
}