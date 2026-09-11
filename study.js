const navLinks = document.querySelectorAll('.nav-link');
const sections = document.querySelectorAll('main section[id]');

const updateActiveNav = () => {
  const current = [...sections].reverse().find(section => window.scrollY >= section.offsetTop - 130);
  navLinks.forEach(link => link.classList.toggle('active', current && link.getAttribute('href') === `#${current.id}`));
};

window.addEventListener('scroll', updateActiveNav, { passive: true });
updateActiveNav();