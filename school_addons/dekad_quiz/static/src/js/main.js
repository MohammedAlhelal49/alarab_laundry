$(document).ready(function () {
const quiz_timer = document.querySelector("#quiz_timer");

let quiz_id = $("#quiz_create_form #quiz_id").val()

console.log(quiz_id)
if  (quiz_id) {
      $.get('/student/quiz/get?quiz_id=' + quiz_id, function (data, status) {
          quizTimer(data);
      })

}





});

function quizTimer(data={}) {
let   hours_html = document.querySelector("#quiz_hours");
let   minutes_html = document.querySelector("#quiz_minutes");
let   seconds_html = document.querySelector("#quiz_seconds");

// Assume these values are fetched from the server
const hour_limit =  data.hour_limit
const minute_limit = data.minute_limit

// Calculate the total time in seconds
const totalSeconds = (hour_limit * 60 * 60) + (minute_limit * 60);

const countdownEnd = new Date();
countdownEnd.setSeconds(countdownEnd.getSeconds() + totalSeconds);

function countdown() {
    const currentDate = new Date();
    const remainingSeconds = Math.max(0, Math.floor((countdownEnd - currentDate) / 1000));
    const hours = Math.floor(remainingSeconds / 3600);
    const minutes = Math.floor((remainingSeconds % 3600) / 60);
    const seconds = Math.floor(remainingSeconds % 60);

    if  (hours_html) {
     hours_html.innerHTML = formatTime(hours);
    }

       if  (minutes_html) {
      minutes_html.innerHTML = formatTime(minutes);
    }

       if   (seconds_html){
   seconds_html.innerHTML = formatTime(seconds);
    }




    // Check if the countdown has reached zero
    if (remainingSeconds === 0) {
    var element = $("#quiz_create_form").submit();
    }
}

function formatTime(time) {
    return time < 10 ? `0${time}` : time;
}

setInterval(countdown, 1000);


}



