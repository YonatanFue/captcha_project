document.addEventListener('DOMContentLoaded', async () => {
    try {
        await fetchCaptchaData(2, 3);

        await fetchLeaderboard();
        await fetchPersonalScore();
    } catch (error) {
        console.error('Error during initialization:', error);
    }
});

async function fetchCaptchaData(captchaNumber, fetchAttempts) {
    return fetch(`/captcha${captchaNumber}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch captcha data');
            }
            return response.json();
        })
        .then(captchaData => {
            const captchaImage = document.getElementById('captcha-image');
            captchaImage.src = `data:image/jpeg;base64,${captchaData.image}`;
            window.captchaAnswerHashed = captchaData.hashed_answer;
            window.captchaNumber = captchaNumber; // difficulty level

            // form submission event listener
            document.getElementById('captcha-form').addEventListener('submit', handleFormSubmission);
        })
        .catch(error => { // trying a few times incase of errors, then go back to main page
            console.error('Error:', error);
            if (fetchAttempts > 0) {
                return fetchCaptchaData(captchaNumber, fetchAttempts - 1);
            } else {
                window.location.href = 'index.html';
                return Promise.reject(error);
            }
        });
}

async function handleFormSubmission(event) {
    event.preventDefault(); // prevent default

    const userAnswer = document.getElementById('captcha-answer').value;

    const hashedUserAnswer = CryptoJS.SHA256(userAnswer).toString(); // same hash as pythons

    const isCaptchaCorrect = (hashedUserAnswer === window.captchaAnswerHashed);

    sendCaptchaVerification(isCaptchaCorrect) // continue after func ends
        .then(success => {
            if (success) {
                document.getElementById('captcha-answer').value = ""; // clear entry

                // updated score
                return fetchPersonalScore();
            } else {
                // incorrect toast
                displayToast('Incorrect Answer. Please try again.');
                return Promise.reject('Incorrect captcha answer');
            }
        })
        .then(() => {
            // Update leaderboard after successful captcha submission
            return fetchLeaderboard();
        })
        .then(() => {
            // new captcha with reset attempts
            fetchCaptchaData(window.captchaNumber, 3);
        })
        .catch(error => {
            console.error('Error:', error);
        });
}


function displayToast(message) {
    const toast = document.createElement('div');
    toast.classList.add('toast');
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // delay fade
    setTimeout(() => {
        toast.classList.add('fade-out');
    }, 500);

    // kill after faded out
    setTimeout(() => {
        toast.remove();
    }, 2000);
}

async function sendCaptchaVerification(isCaptchaCorrect) {
    //result data
    const username = getCookie('username');
    const requestData = {
        username: username,
        isCaptchaCorrect: isCaptchaCorrect.toString()
    };

    return fetch('/captcha_attempt', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams(requestData).toString() // send
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            return true;
        } else {
            console.log("Failed to update score");
            return false;
        }
    })
    .catch(error => {
        console.error('Error updating score:', error);
        return false;
    });
}

async function fetchLeaderboard() {
    return fetch('/leaderboard')
        .then(response => response.json())
        .then(leaderboard => {
            const leaderboardElement = document.getElementById('leaderboard');
            leaderboardElement.innerHTML = ''; // clear previous
            leaderboard.forEach((entry, index) => { // create the leaderboard
                const listItem = document.createElement('li');
                listItem.textContent = `${index + 1}. ${entry.username} - ${entry.score}`;
                leaderboardElement.appendChild(listItem);
            });
        })
        .catch(error => console.error('Error fetching leaderboard:', error));
}

async function fetchPersonalScore() {
    const username = getCookie('username');
    if (username) {
        return fetch(`/username`)
            .then(response => response.json())
            .then(user => {
                if (user.username) {
                    document.getElementById('personal-score').textContent = `Your Score: ${user.score}`;
                } else {
                    document.getElementById('personal-score').textContent = 'Your Score: 0';
                }
            })
            .catch(error => console.error('Error fetching personal score:', error));
    } else {
        document.getElementById('personal-score').textContent = 'Your Score: 0';
        return Promise.resolve();
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}