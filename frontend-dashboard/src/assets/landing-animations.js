export function initLandingPage() {
  /* ===== NEURAL NETWORK CANVAS ===== */
  const canvas = document.getElementById('neural-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let w, h, nodes = [], mouse = { x: -1000, y: -1000 };
    const NODE_COUNT = 80, CONNECT_DIST = 160;

    function resize() {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);
    
    // Clean up previous event listeners if needed, simple approach for now
    document.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });

    class Node {
      constructor() { this.reset(); }
      reset() {
        this.x = Math.random() * w;
        this.y = Math.random() * h;
        this.vx = (Math.random() - 0.5) * 0.4;
        this.vy = (Math.random() - 0.5) * 0.4;
        this.r = Math.random() * 2 + 1;
      }
      update() {
        this.x += this.vx; this.y += this.vy;
        if (this.x < 0 || this.x > w) this.vx *= -1;
        if (this.y < 0 || this.y > h) this.vy *= -1;
      }
    }

    for (let i = 0; i < NODE_COUNT; i++) nodes.push(new Node());
    
    // Prevent multiple animation loops if initialized multiple times
    if(window._canvasAnimFrame) cancelAnimationFrame(window._canvasAnimFrame);

    function draw() {
      ctx.clearRect(0, 0, w, h);
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        a.update();
        const dm = Math.hypot(a.x - mouse.x, a.y - mouse.y);
        const glow = dm < 200 ? 1 - dm / 200 : 0;
        ctx.beginPath();
        ctx.arc(a.x, a.y, a.r + glow * 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(59,130,246,${0.3 + glow * 0.5})`;
        ctx.fill();
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < CONNECT_DIST) {
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(139,92,246,${0.08 * (1 - d / CONNECT_DIST)})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }
      window._canvasAnimFrame = requestAnimationFrame(draw);
    }
    draw();
  }

  /* ===== SCROLL PROGRESS BAR ===== */
  const scrollProgress = document.getElementById('scroll-progress');
  window.addEventListener('scroll', () => {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = (scrollTop / docHeight) * 100;
    if (scrollProgress) scrollProgress.style.width = progress + '%';
  });

  /* ===== CUSTOM CURSOR GLOW ===== */
  const cursorGlow = document.getElementById('cursor-glow');
  let cursorX = 0, cursorY = 0, cursorTargetX = 0, cursorTargetY = 0;
  document.addEventListener('mousemove', e => {
    cursorTargetX = e.clientX;
    cursorTargetY = e.clientY;
    if (cursorGlow && !cursorGlow.classList.contains('visible')) cursorGlow.classList.add('visible');
  });
  
  if(window._cursorAnimFrame) cancelAnimationFrame(window._cursorAnimFrame);
  function animateCursor() {
    cursorX += (cursorTargetX - cursorX) * 0.15;
    cursorY += (cursorTargetY - cursorY) * 0.15;
    if (cursorGlow) {
      cursorGlow.style.left = cursorX + 'px';
      cursorGlow.style.top = cursorY + 'px';
    }
    window._cursorAnimFrame = requestAnimationFrame(animateCursor);
  }
  animateCursor();

  document.querySelectorAll('a, button, .feature-card, .integration-card, .tech-card').forEach(el => {
    el.addEventListener('mouseenter', () => cursorGlow && cursorGlow.classList.add('hovering'));
    el.addEventListener('mouseleave', () => cursorGlow && cursorGlow.classList.remove('hovering'));
  });

  /* ===== MOUSE SPOTLIGHT ===== */
  const spotlight = document.getElementById('mouse-spotlight');
  document.addEventListener('mousemove', e => {
    if (spotlight) {
      spotlight.style.left = e.clientX + 'px';
      spotlight.style.top = e.clientY + 'px';
    }
  });

  /* ===== NAVBAR SCROLL ===== */
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if(navbar) navbar.classList.toggle('scrolled', window.scrollY > 40);
  });

  /* ===== MOBILE TOGGLE ===== */
  const mobileToggle = document.getElementById('mobile-toggle');
  const navLinks = document.getElementById('nav-links');
  if (mobileToggle) {
    mobileToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
    });
  }

  /* ===== COUNTER ANIMATION ===== */
  function animateCounters() {
    document.querySelectorAll('.stat-number[data-target]').forEach(el => {
      const target = +el.getAttribute('data-target');
      const duration = 1500;
      const start = performance.now();
      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased);
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }

  /* ===== 3D TILT EFFECT ON CARDS ===== */
  function initTiltCards() {
    const tiltables = document.querySelectorAll('.feature-card:not(.featured), .integration-card, .tech-card');
    tiltables.forEach(card => {
      if(!card.querySelector('.card-shine')) {
        const shine = document.createElement('div');
        shine.classList.add('card-shine');
        card.appendChild(shine);
      }

      card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const rotateX = ((y - centerY) / centerY) * -8;
        const rotateY = ((x - centerX) / centerX) * 8;

        card.classList.add('tilt-active');
        card.style.transform = `perspective(1200px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(10px)`;

        const shineX = (x / rect.width) * 100;
        const shineY = (y / rect.height) * 100;
        card.style.setProperty('--shine-x', shineX + '%');
        card.style.setProperty('--shine-y', shineY + '%');
      });

      card.addEventListener('mouseleave', () => {
        card.classList.remove('tilt-active');
        card.style.transform = '';
      });
    });
  }

  /* ===== MAGNETIC BUTTON EFFECT ===== */
  function initMagneticButtons() {
    document.querySelectorAll('.btn-primary, .btn-outline').forEach(btn => {
      btn.classList.add('btn-magnetic');
      btn.addEventListener('mousemove', e => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = `translate(${x * 0.15}px, ${y * 0.15}px)`;
      });
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = '';
      });
    });
  }

  /* ===== TEXT SCRAMBLE ON REVEAL ===== */
  function scrambleText(element) {
    const chars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    const original = element.textContent;
    const duration = 800;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const revealed = Math.floor(progress * original.length);
      let result = '';
      for (let i = 0; i < original.length; i++) {
        if (original[i] === ' ') { result += ' '; continue; }
        if (i < revealed) {
          result += original[i];
        } else {
          result += chars[Math.floor(Math.random() * chars.length)];
        }
      }
      element.textContent = result;
      if (progress < 1) requestAnimationFrame(tick);
      else element.textContent = original;
    }
    requestAnimationFrame(tick);
  }

  /* ===== FLOATING PARTICLES IN HERO ===== */
  function initHeroParticles() {
    const hero = document.querySelector('.hero-visual');
    if (!hero) return;
    if(window._particleInterval) clearInterval(window._particleInterval);
    window._particleInterval = setInterval(() => {
      const particle = document.createElement('div');
      particle.classList.add('hero-particle');
      particle.style.left = Math.random() * 100 + '%';
      particle.style.bottom = '20%';
      particle.style.animationDuration = (2 + Math.random() * 3) + 's';
      particle.style.width = (2 + Math.random() * 4) + 'px';
      particle.style.height = particle.style.width;
      particle.style.background = Math.random() > 0.5 ? 'rgba(59,130,246,0.5)' : 'rgba(139,92,246,0.5)';
      hero.appendChild(particle);
      setTimeout(() => particle.remove(), 5000);
    }, 400);
  }

  /* ===== AI TERMINAL ANIMATION ===== */
  function initTerminalAnimation() {
    const body = document.getElementById('terminal-body');
    if (!body) return;

    const lines = [
      { delay: 400, html: '<span class="t-info">INFO</span>:     <span class="t-dim">FastAPI server started on</span> <span class="t-bold">0.0.0.0:8000</span>' },
      { delay: 600, html: '<span class="t-success">✓</span> <span class="t-dim">MongoDB connected</span>  <span class="t-success">✓</span> <span class="t-dim">Pinecone ready</span>  <span class="t-success">✓</span> <span class="t-dim">Groq LLM bound</span>' },
      { delay: 800, html: '' },
      { delay: 300, html: '<span class="t-info">▸ POST</span> <span class="t-dim">/chat</span>  <span class="t-purple">user:</span> <span class="t-bold">"Build a mobile banking app for our fintech team"</span>' },
      { delay: 500, html: '' },
      { delay: 200, html: '<span class="t-warning">⚡ Agent</span> <span class="t-dim">reasoning...</span>' },
      { delay: 600, html: '<span class="t-cyan">  ↳ Intent detected:</span> <span class="t-bold">PROJECT_PLANNING</span>' },
      { delay: 400, html: '<span class="t-cyan">  ↳ Tool selected:</span>  <span class="t-purple">execute_project_plan</span>' },
      { delay: 500, html: '' },
      { delay: 200, html: '<span class="t-info">🧠 Decomposing goal → 8 tasks generated</span>' },
      { delay: 300, html: '<span class="t-dim">   ┌─ T1: API Architecture Design</span>       <span class="t-cyan">→ backend_lead</span>   <span class="t-dim">2d</span>' },
      { delay: 250, html: '<span class="t-dim">   ├─ T2: Database Schema (PostgreSQL)</span>  <span class="t-cyan">→ db_engineer</span>   <span class="t-dim">1d</span>' },
      { delay: 250, html: '<span class="t-dim">   ├─ T3: Auth + JWT Implementation</span>    <span class="t-cyan">→ backend_lead</span>  <span class="t-dim">2d</span>' },
      { delay: 250, html: '<span class="t-dim">   ├─ T4: React Native UI Screens</span>      <span class="t-cyan">→ mobile_dev</span>    <span class="t-dim">3d</span>' },
      { delay: 250, html: '<span class="t-dim">   ├─ T5: Payment Gateway Integration</span>  <span class="t-cyan">→ backend_lead</span>  <span class="t-dim">2d</span>' },
      { delay: 250, html: '<span class="t-dim">   ├─ T6: Unit + Integration Tests</span>     <span class="t-cyan">→ qa_engineer</span>   <span class="t-dim">2d</span>' },
      { delay: 250, html: '<span class="t-dim">   ├─ T7: CI/CD Pipeline Setup</span>         <span class="t-cyan">→ devops</span>        <span class="t-dim">1d</span>' },
      { delay: 250, html: '<span class="t-dim">   └─ T8: App Store Submission</span>         <span class="t-cyan">→ mobile_dev</span>    <span class="t-dim">1d</span>' },
      { delay: 400, html: '' },
      { delay: 300, html: '<span class="t-info">📊 Topological sort → dependency chain resolved</span>' },
      { delay: 300, html: '<span class="t-info">📅 Smart timeline → weekends skipped, 14 business days</span>' },
      { delay: 400, html: '<span class="t-warning">💰 Budget: $18,400</span> <span class="t-dim">(personnel: $16,800 + tools: $1,600)</span>' },
      { delay: 600, html: '' },
      { delay: 300, html: '<span class="t-success">✅ Plan staged → awaiting manager approval</span>' },
      { delay: 500, html: '' },
      { delay: 300, html: '<span class="t-info">▸ POST</span> <span class="t-dim">/approve</span>  <span class="t-success">Manager approved the plan</span>' },
      { delay: 500, html: '' },
      { delay: 200, html: '<span class="t-warning">⚡ Executing plan...</span>' },
      { delay: 400, html: '<span class="t-success">  ✓</span> <span class="t-dim">Trello card created:</span> <span class="t-bold">T1: API Architecture Design</span> <span class="t-dim">[🟢 On Budget]</span>' },
      { delay: 350, html: '<span class="t-success">  ✓</span> <span class="t-dim">Focus time booked in Google Calendar for</span> <span class="t-cyan">backend_lead</span>' },
      { delay: 300, html: '<span class="t-success">  ✓</span> <span class="t-dim">Slack notification sent to</span> <span class="t-bold">#project-updates</span>' },
      { delay: 500, html: '<span class="t-success">  ✓</span> <span class="t-dim">All 8 cards created · 8 calendar blocks · 8 Slack messages</span>' },
      { delay: 600, html: '' },
      { delay: 300, html: '<span class="t-info">🔁 heal_project_schedule</span> <span class="t-dim">→ scanning for overdue tasks...</span>' },
      { delay: 400, html: '<span class="t-success">  ✓ No overdue tasks detected. Schedule is healthy.</span>' },
      { delay: 500, html: '<span class="t-dim">────────────────────────────────────────</span>' },
      { delay: 300, html: '<span class="t-success">🎯 Project "Mobile Banking App" is fully operational.</span><span class="terminal-cursor"></span>' },
    ];

    let terminalStarted = false;
    if(window._terminalObserver) window._terminalObserver.disconnect();
    window._terminalObserver = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !terminalStarted) {
        terminalStarted = true;
        let totalDelay = 0;
        lines.forEach(line => {
          totalDelay += line.delay;
          setTimeout(() => {
            if(!document.getElementById('terminal-body')) return;
            const div = document.createElement('div');
            div.classList.add('terminal-line');
            div.innerHTML = line.html || '&nbsp;';
            body.appendChild(div);
            body.scrollTop = body.scrollHeight;
          }, totalDelay);
        });
        setTimeout(() => {
          terminalStarted = false;
          while (body.children.length > 1) body.removeChild(body.lastChild);
        }, totalDelay + 3000);
      }
    }, { threshold: 0.3 });

    window._terminalObserver.observe(body.closest('.terminal-window'));
  }

  /* ===== SCROLL REVEAL ===== */
  const revealElements = document.querySelectorAll(
    '.section-header, .pipeline-step, .feature-card, .arch-layer, .integration-card, .demo-showcase, .tech-card, .cta-card, .terminal-window'
  );
  revealElements.forEach(el => el.classList.add('reveal'));

  let countersAnimated = false;
  if(window._revealObserver) window._revealObserver.disconnect();
  window._revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        if (entry.target.classList.contains('section-header')) {
          const title = entry.target.querySelector('.section-title');
          if (title && !title.getAttribute('data-scrambled')) {
            title.setAttribute('data-scrambled', 'true');
            scrambleText(title);
          }
        }
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

  revealElements.forEach(el => window._revealObserver.observe(el));

  const heroStats = document.querySelector('.hero-stats');
  if (heroStats) {
    if(window._statsObserver) window._statsObserver.disconnect();
    window._statsObserver = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !countersAnimated) {
        countersAnimated = true;
        animateCounters();
      }
    }, { threshold: 0.5 });
    window._statsObserver.observe(heroStats);
  }

  /* ===== DEMO TABS ===== */
  document.querySelectorAll('.demo-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.demo-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.demo-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const targetPanel = document.getElementById('panel-' + tab.getAttribute('data-tab'));
      if(targetPanel) targetPanel.classList.add('active');
    });
  });

  /* ===== SMOOTH ANCHOR SCROLL ===== */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
        const navLinks = document.getElementById('nav-links');
        if (navLinks) navLinks.classList.remove('open');
      }
    });
  });

  /* ===== STAGGERED REVEAL ===== */
  document.querySelectorAll('.features-grid, .integrations-grid, .tech-grid, .pipeline, .arch-diagram').forEach(grid => {
    const children = grid.querySelectorAll('.reveal');
    children.forEach((child, i) => {
      child.style.transitionDelay = `${i * 80}ms`;
    });
  });

  /* ===== PARALLAX HERO IMAGE ===== */
  const heroImage = document.querySelector('.hero-image-wrapper');
  if (heroImage) {
    window.addEventListener('scroll', () => {
      const scrolled = window.scrollY;
      if (scrolled < window.innerHeight && heroImage) {
        heroImage.style.transform = `translateY(${scrolled * 0.08}px)`;
      }
    });
  }

  initTiltCards();
  initMagneticButtons();
  initHeroParticles();
  initTerminalAnimation();
}
