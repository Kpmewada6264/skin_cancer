function validateRegister() {
  const password = document.querySelector('input[name="password"]').value;
  const confirm = document.querySelector('input[name="confirm"]').value;
  if (password !== confirm) {
    alert("Passwords do not match!");
    return false;
  }
  return true;
}
