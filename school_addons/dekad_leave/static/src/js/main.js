$(document).ready(function () {
  var path = window.location.pathname
  let leaves = []
  if (path.includes('/student/leave/create')) {
    handle('create')
    submitForm('create')
  }
  if (path.includes('/student/leave/update')) {
    handle('update')
    submitForm('update')
  }
  function handle(key) {
    if (key == "create") {
      student_id = $("#leave_create_form #student_id").val()
      $.get('/student/leaves/get/', function (data, status) {
        leaves = data
      })
    }
    else {
      student_id = $("#leave_update_form #student_id").val()
      record_id = $("#leave_update_form #record_id").val()
      $.get('/student/leaves/get?student_id=' + student_id, function (data, status) {
        leaves = data.filter((leave) => {
          return leave.id != record_id
        })
      })
    }
  }
  function validateForm(key) {
    const createKey = key === "create";
    const errorElement = createKey ? $('#leave_create_error') : $('#leave_update_error');
    const startDateField = createKey ? $('#leave_create_form #start_date') : $('#leave_update_form #start_date');
    const endDateField = createKey ? $('#leave_create_form #end_date') : $('#leave_update_form #end_date');
    const startDateValue = handleInterfaceDateFormat(startDateField.val());
    const endDateValue = handleInterfaceDateFormat(endDateField.val());
    const studentId = createKey ? $("#leave_create_form #student_id").val() : $("#leave_update_form #student_id").val();
    const errors = [];

    const currentDate = new Date().toISOString().split('T')[0]; // Format current date as YYYY-MM-DD

    // Validate date ranges
    if (startDateValue > endDateValue) {
        errors.push('End Date cannot be less than Start Date.');
    }
    if (startDateValue < currentDate) {
        errors.push('Start Date cannot be less than today.');
    }

    // Validate overlapping leaves
    leaves.forEach((leave) => {
        const leaveStartDate = leave.start_date;
        const leaveEndDate = leave.end_date;
        const leaveStudentId = leave.student_id;

        const leaveInsideRequest =
            (leaveStartDate >= startDateValue && leaveStartDate <= endDateValue) ||
            (leaveEndDate >= startDateValue && leaveEndDate <= endDateValue);

        const requestInsideLeave =
            (startDateValue >= leaveStartDate && startDateValue <= leaveEndDate) ||
            (endDateValue >= leaveStartDate && endDateValue <= leaveEndDate);

        if (leaveStartDate === startDateValue && leaveEndDate === endDateValue && studentId === leaveStudentId) {
            errors.push(`Student already has this leave (${startDateField.val()} - ${endDateField.val()}).`);
        }

        if (leaveInsideRequest || requestInsideLeave) {
            errors.push(`Student Leave overlaps with another leave (${leaveStartDate} - ${leaveEndDate}).`);
        }
    });

    // Display error if any
    if (errors.length) {
        errorElement.css("display", "block").text(errors[0]);
    }

    return errors.length;
}

  function submitForm(key) {
    createKye = key == "create"
    var element = createKye ? $("#leave_create_form") : $("#leave_update_form")
    var message = createKye ? "New leave created" : "Update leave data"
    element.submit(function (event) {
    event.preventDefault();
      if (!validateForm(key)) {
        this.submit();
      }
    });
  }
  function handleInterfaceDateFormat (dateValue) {


                var dateParts = dateValue.split('/');

                // Create a new Date object with the parts
                var dateObject = new Date(dateParts[2], dateParts[1] - 1, dateParts[0]);

                // Format the date as yyyy-mm-dd
                var formattedDate = dateObject.getFullYear() + '-' + ('0' + (dateObject.getMonth() + 1)).slice(-2) + '-' + ('0' + dateObject.getDate()).slice(-2);

//              console.log(formattedDate)
              return formattedDate
  }
});

