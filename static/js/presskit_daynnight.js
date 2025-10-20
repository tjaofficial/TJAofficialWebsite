document.addEventListener("DOMContentLoaded", () => {
  const dl = document.getElementById("pk-download");
  if (dl) dl.addEventListener("click", () => window.print());
});
