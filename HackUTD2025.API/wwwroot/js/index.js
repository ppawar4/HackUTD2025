// Dynamic year
document.getElementById('year').textContent = new Date().getFullYear();

// Build a simple TOC from h2 sections
const toc = document.getElementById('toc-links');
const sections = Array.from(document.querySelectorAll('main .panel'));
sections.forEach(sec => {
    const h2 = sec.querySelector('h2');
    if (!h2 || !sec.id) return;
    const a = document.createElement('a');
    a.href = '#' + sec.id;
    a.textContent = h2.textContent.replace(/\\s+#$/, '');
    toc.appendChild(a);
});

// Highlight current section in TOC
const tocLinks = Array.from(toc.querySelectorAll('a'));
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            tocLinks.forEach(l => l.classList.remove('current'));
            const active = tocLinks.find(l => l.getAttribute('href') === '#' + e.target.id);
            if (active) active.classList.add('current');
        }
    });
}, {rootMargin: '-40% 0px -50% 0px', threshold: 0});
sections.forEach(s => observer.observe(s));

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (ev) => {
        const id = a.getAttribute('href').slice(1);
        const el = document.getElementById(id);
        if (el) {
            ev.preventDefault();
            el.scrollIntoView({behavior: 'smooth', block: 'start'});
            history.pushState(null, '', '#' + id);
        }
    });
});