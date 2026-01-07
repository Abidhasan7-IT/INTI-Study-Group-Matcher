// Store all groups for search functionality
let allGroups = [];

// When the page loads, show the user's groups
document.addEventListener('DOMContentLoaded', function() {
    // Get the list element where groups will be displayed
    const myGroupsList = document.getElementById('myGroupsList');

    // Get search elements
    const searchInput = document.getElementById('searchJoinedGroups');
    const searchBtn = document.getElementById('searchJoinedGroupsBtn');
    const clearBtn = document.getElementById('clearSearchBtn');

    // Get current user from session
    fetch('/api/user')
        .then(response => {
            if (!response.ok) {
                myGroupsList.innerHTML = '<p>Please log in to view your groups. Go to "Find Group" to join one!</p>';
                return;
            }
            return response.json();
        })
        .then(userData => {
            if (!userData) {
                myGroupsList.innerHTML = '<p>Please log in to view your groups. Go to "Find Group" to join one!</p>';
                return;
            }
            
            // Fetch user's groups from backend
            fetch('/my-groups?format=json')
                .then(response => response.json())
                .then(groups => {
                    // Store all groups for search functionality
                    allGroups = groups;
                    
                    // If no groups, show a message
                    if (groups.length === 0) {
                        myGroupsList.innerHTML = '<p>You haven\u2019t joined or created any groups yet. Go to "Find Group" to join one or "Create Group" to start your own!</p>';
                        return;
                    }

                    // Display all groups initially
                    displayGroups(groups);
                })
                .catch(error => {
                    console.error('Error fetching user groups:', error);
                    myGroupsList.innerHTML = '<p>Error loading your groups. Please try again later.</p>';
                });
        })
        .catch(error => {
            console.error('Error getting user info:', error);
            myGroupsList.innerHTML = '<p>Please log in to view your groups. Go to "Find Group" to join one!</p>';
        });

    // Add event listener for search button
    searchBtn.addEventListener('click', function() {
        const searchTerm = searchInput.value.trim().toLowerCase();
        if (searchTerm) {
            performSearch(searchTerm);
        } else {
            displayGroups(allGroups);
        }
    });

    // Add event listener for Enter key in search input
    searchInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            const searchTerm = searchInput.value.trim().toLowerCase();
            if (searchTerm) {
                performSearch(searchTerm);
            } else {
                displayGroups(allGroups);
            }
        }
    });

    // Add event listener for clear button
    clearBtn.addEventListener('click', function() {
        searchInput.value = '';
        displayGroups(allGroups);
    });
});

// Function to perform search on groups
function performSearch(searchTerm) {
    const filteredGroups = allGroups.filter(group => {
        const subjectName = getFriendlySubjectName(group.subject).toLowerCase();
        const goalName = getFriendlyGoalName(group.goal).toLowerCase();
        const groupId = group.id.toString().toLowerCase();
        const location = (group.location || '').toLowerCase();
        
        return (
            subjectName.includes(searchTerm) ||
            goalName.includes(searchTerm) ||
            groupId.includes(searchTerm) ||
            location.includes(searchTerm)
        );
    });
    
    // Maintain descending order by creation date
    filteredGroups.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    displayGroups(filteredGroups);
}

// Function to display groups in the UI
function displayGroups(groups) {
    const myGroupsList = document.getElementById('myGroupsList');
    
    if (groups.length === 0) {
        myGroupsList.innerHTML = '<p>No groups found matching your search criteria.</p>';
        return;
    }
    
    myGroupsList.innerHTML = '';
    
    // Create a container for the group cards to apply grid layout
    const groupsContainer = document.createElement('div');
    groupsContainer.className = 'groups-container';
    
    groups.forEach(group => {
        const groupCard = document.createElement('div');
        
        // Set different class based on group type
        if (group.type === 'created') {
            groupCard.className = 'group-card created-group';
        } else {
            groupCard.className = 'group-card joined-group';
        }
        
        // Convert subject code to friendly name (e.g., "math101" → "Math 101")
        const subjectName = getFriendlySubjectName(group.subject);
        // Convert goal code to friendly name (e.g., "midterm" → "Midterm Review")
        const goalName = getFriendlyGoalName(group.goal);
        
        // Add different header text based on group type
        const groupTypeText = group.type === 'created' ? 'Created Group' : 'Joined Group';
        
        groupCard.innerHTML = `
            <h3>${subjectName} Study Group <span class="group-type">(${groupTypeText})</span></h3>
            <p><strong>Group ID:</strong> ${group.id}</p>
            <p><strong>Purpose:</strong> ${goalName}</p>
            <p><strong>Date/Time:</strong> ${group.date} • ${group.time}</p>
            <p><strong>Location:</strong> ${group.location}</p>
            <p><strong>Members:</strong> ${group.current_members}/${group.max_members}</p>
            <p><strong>Created by:</strong> ${group.creator}</p>
            <a href="/group/${group.id}" class="btn btn-success">Details</a>
            ${group.type === 'created' ? `<button class="btn btn-danger delete-group-btn" data-group-id="${group.id}">Delete</button>` : ''}
        `;
        groupsContainer.appendChild(groupCard);
    });
    
    // Add the container to the groups list
    myGroupsList.appendChild(groupsContainer);
    
    // Add event listeners for delete buttons
    document.querySelectorAll('.delete-group-btn').forEach(button => {
        button.addEventListener('click', function() {
            const groupId = this.getAttribute('data-group-id');
            deleteGroup(groupId);
        });
    });
}

// Function to delete a group
function deleteGroup(groupId) {
    if (confirm('Are you sure you want to delete this group? All members will be removed from the group.')) {
        fetch(`/user-delete-group/${groupId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Group deleted successfully');
                // Refresh the groups list
                location.reload();
            } else {
                alert('Error deleting group: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting group');
        });
    }
}

// Helper function: Convert subject code to friendly name
function getFriendlySubjectName(subjectCode) {
    const subjects = {
        'math101': 'Math 101',
        'prog101': 'Programming Fundamentals',
        'bus101': 'Business Ethics',
        'stats101': 'Statistics 101'
    };
    return subjects[subjectCode] || subjectCode;
}

// Helper function: Convert goal code to friendly name
function getFriendlyGoalName(goalCode) {
    const goals = {
        'midterm': 'Midterm Review',
        'homework': 'Homework Help',
        'project': 'Project Discussion',
        'final': 'Final Exam Prep'
    };
    return goals[goalCode] || goalCode;
}