// Run when form is submitted
document.getElementById('groupForm').addEventListener('submit', function(e) {
    e.preventDefault(); // Stop page reload

    // Get form values
    const subject = document.getElementById('subject').value;
    const goal = document.getElementById('goal').value;
    const date = document.getElementById('date').value;
    const time = document.getElementById('time').value;
    const locationValue = document.getElementById('location').value;
    const maxMembers = document.getElementById('maxMembers').value || 5;

    // Validate required fields
    if (!subject || !goal || !date || !time || !locationValue) {
        alert('Please fill in all required fields');
        return;
    }

    // Get current user info from session
    fetch('/api/user')
        .then(response => {
            if (!response.ok) {
                // If user is not authenticated, redirect to login
                if (response.status === 401) {
                    alert('Please log in first to create a group');
                    window.location.href = '/login';
                    return;
                }
                throw new Error('User not authenticated');
            }
            return response.json();
        })
        .then(userData => {
            console.log('User data received:', userData); // Debug log
            // Prepare group data
            const groupData = {
                subject: subject,
                goal: goal,
                date: date,
                time: time,
                location: locationValue, // Changed from 'location' to 'locationValue' to avoid conflict with global location object
                maxMembers: parseInt(maxMembers),
                created_by: userData.id
            };

            // Send to backend
            fetch('/create-group', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(groupData)
            })
            .then(response => {
                console.log('Response status:', response.status); // Debug log
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data); // Debug log
                if (data.error) {
                    alert(`Error creating group: ${data.error}`);
                } else if (data.group_id) {
                    alert(`Success! Group created successfully.\nGroup ID: ${data.group_id}`);
                    window.location.href = '/my-groups';
                } else {
                    // Fallback: if no error but no group_id, show generic success
                    alert('Group created successfully!');
                    window.location.href = '/my-groups';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while creating the group: ' + error.message);
            });
        })
        .catch(error => {
            console.error('Error getting user info:', error);
            alert('Please log in first to create a group');
            window.location.href = '/login';
        });
});