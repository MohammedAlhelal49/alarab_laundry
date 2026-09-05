$( document ).ready(function() {
passwordToggle();
});
function passwordToggle () {
$("form input[type|='password']").next().on('click' , function () {
  $type = $(this).prev().attr( "type" );
  if ($type == 'password') {
    $(this).prev().attr( "type" , "text" );
    $(this).removeClass("fa-eye").addClass('fa-eye-slash');
  }
  else {
   $(this).prev().attr( "type" , "password" );
     $(this).removeClass("fa-eye-slash").addClass('fa-eye');
  }
})
}


