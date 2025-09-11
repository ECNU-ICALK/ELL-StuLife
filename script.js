// DOM elements
const hamburger = document.querySelector('.hamburger');
const navMenu = document.querySelector('.nav-menu');
const navLinks = document.querySelectorAll('.nav-link[data-section]');
const sections = document.querySelectorAll('.section');

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize page state
    showSection('home');
    
    // Setup navigation link event listeners
    setupNavigationListeners();
    
    // Setup mobile menu
    setupMobileMenu();
    
    // Setup scroll effects
    setupScrollEffects();
    
    // Setup animations
    setupAnimations();
});

// Setup navigation link event listeners
function setupNavigationListeners() {
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetSection = this.getAttribute('data-section');
            if (targetSection) {
                showSection(targetSection);
                updateActiveNavLink(this);
                
                // Close menu on mobile
                if (navMenu.classList.contains('active')) {
                    toggleMobileMenu();
                }
            }
        });
    });
}

// Show specified section
function showSection(sectionId) {
    // Hide all sections
    sections.forEach(section => {
        section.classList.remove('active');
    });
    
    // Show target section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Trigger animations
        triggerSectionAnimations(targetSection);
    }
}

// Update active navigation link
function updateActiveNavLink(activeLink) {
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    activeLink.classList.add('active');
}

// Setup mobile menu
function setupMobileMenu() {
    hamburger.addEventListener('click', toggleMobileMenu);
    
    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (navMenu.classList.contains('active') && 
            !navMenu.contains(e.target) && 
            !hamburger.contains(e.target)) {
            toggleMobileMenu();
        }
    });
}

// Toggle mobile menu
function toggleMobileMenu() {
    hamburger.classList.toggle('active');
    navMenu.classList.toggle('active');
    
    // Animate hamburger menu icon
    const bars = hamburger.querySelectorAll('.bar');
    if (hamburger.classList.contains('active')) {
        bars[0].style.transform = 'rotate(-45deg) translate(-5px, 6px)';
        bars[1].style.opacity = '0';
        bars[2].style.transform = 'rotate(45deg) translate(-5px, -6px)';
    } else {
        bars[0].style.transform = 'none';
        bars[1].style.opacity = '1';
        bars[2].style.transform = 'none';
    }
}

// Setup scroll effects
function setupScrollEffects() {
    let lastScrollTop = 0;
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Navbar scroll effect
        if (scrollTop > lastScrollTop && scrollTop > 100) {
            // Scrolling down, hide navbar
            navbar.style.transform = 'translateY(-100%)';
        } else {
            // Scrolling up, show navbar
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
        
        // Parallax effect when scrolling
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.framework-img, .stulife-img, .architecture-img');
        parallaxElements.forEach(element => {
            const speed = 0.5;
            element.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });
}

// Setup animations
function setupAnimations() {
    // Create observer to trigger animations when entering viewport
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // Observe elements that need animation
    const animateElements = document.querySelectorAll('.about-card, .table-card, .citation-card, .principle-card');
    animateElements.forEach(el => {
        observer.observe(el);
    });
}

// Trigger section animations
function triggerSectionAnimations(section) {
    const animatedElements = section.querySelectorAll('.about-card, .table-card, .citation-card');
    animatedElements.forEach((element, index) => {
        setTimeout(() => {
            element.style.animation = `fadeInUp 0.6s ease-out ${index * 0.1}s both`;
        }, index * 100);
    });
}

// Copy citation functionality
function copyCitation() {
    const citationText = document.getElementById('citation-text').textContent;
    
    // Use modern clipboard API
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(citationText).then(() => {
            showCopyFeedback(true);
        }).catch(() => {
            fallbackCopyToClipboard(citationText);
        });
    } else {
        // Fallback solution
        fallbackCopyToClipboard(citationText);
    }
}

// Fallback copy solution
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showCopyFeedback(true);
    } catch (err) {
        showCopyFeedback(false);
    }
    
    document.body.removeChild(textArea);
}

// Show copy feedback
function showCopyFeedback(success) {
    const copyBtn = document.querySelector('.copy-btn');
    const originalText = copyBtn.innerHTML;
    
    if (success) {
        copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
        copyBtn.style.background = 'linear-gradient(135deg, #4caf50, #8bc34a)';
    } else {
        copyBtn.innerHTML = '<i class="fas fa-times"></i> Copy Failed';
        copyBtn.style.background = 'linear-gradient(135deg, #f44336, #ff9800)';
    }
    
    setTimeout(() => {
        copyBtn.innerHTML = originalText;
        copyBtn.style.background = 'linear-gradient(135deg, #667eea, #764ba2)';
    }, 2000);
}

// Smooth scroll to anchor
function smoothScrollTo(targetId) {
    const target = document.getElementById(targetId);
    if (target) {
        const offsetTop = target.offsetTop - 80; // Consider navbar height
        window.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
        });
    }
}

// Handle keyboard navigation
document.addEventListener('keydown', function(e) {
    // ESC key closes mobile menu
    if (e.key === 'Escape' && navMenu.classList.contains('active')) {
        toggleMobileMenu();
    }
    
    // Arrow key navigation (optional feature)
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        const currentSection = document.querySelector('.section.active');
        if (currentSection) {
            const allSections = Array.from(sections);
            const currentIndex = allSections.indexOf(currentSection);
            
            let nextIndex;
            if (e.key === 'ArrowLeft') {
                nextIndex = currentIndex > 0 ? currentIndex - 1 : allSections.length - 1;
            } else {
                nextIndex = currentIndex < allSections.length - 1 ? currentIndex + 1 : 0;
            }
            
            const nextSection = allSections[nextIndex];
            const sectionId = nextSection.id;
            showSection(sectionId);
            
            // Update navbar active state
            const correspondingNavLink = document.querySelector(`[data-section="${sectionId}"]`);
            if (correspondingNavLink) {
                updateActiveNavLink(correspondingNavLink);
            }
        }
    }
});

// Handle table responsiveness
function handleTableResponsiveness() {
    const tables = document.querySelectorAll('.results-table');
    tables.forEach(table => {
        const wrapper = table.closest('.table-container');
        if (table.offsetWidth > wrapper.offsetWidth) {
            wrapper.classList.add('scroll-hint');
        }
    });
}

// Add table scroll hint
function addTableScrollHint() {
    const tableContainers = document.querySelectorAll('.table-container');
    tableContainers.forEach(container => {
        const table = container.querySelector('.results-table');
        if (table && table.offsetWidth > container.offsetWidth) {
            // Add scroll hint
            const hint = document.createElement('div');
            hint.className = 'scroll-hint';
            hint.innerHTML = '<i class="fas fa-arrows-alt-h"></i> Scroll horizontally to view more';
            hint.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                background: rgba(102, 126, 234, 0.9);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 0.8rem;
                pointer-events: none;
                z-index: 10;
            `;
            container.style.position = 'relative';
            container.appendChild(hint);
            
            // Hide hint when scrolling
            container.addEventListener('scroll', function() {
                hint.style.opacity = this.scrollLeft > 10 ? '0' : '1';
            });
        }
    });
}

// Performance optimization: debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Handle window resize
window.addEventListener('resize', debounce(function() {
    // Recalculate table responsiveness
    handleTableResponsiveness();
    
    // If switching to desktop with mobile menu open, close menu
    if (window.innerWidth > 768 && navMenu.classList.contains('active')) {
        toggleMobileMenu();
    }
}, 250));

// Additional setup after page load
window.addEventListener('load', function() {
    // Handle table responsiveness
    handleTableResponsiveness();
    addTableScrollHint();
    
    // Preload images
    const images = document.querySelectorAll('img[src*="github.com"]');
    images.forEach(img => {
        const newImg = new Image();
        newImg.src = img.src;
    });
});

// Error handling
window.addEventListener('error', function(e) {
    console.error('Page error:', e.error);
});

// Add some utility functions
const utils = {
    // Detect mobile device
    isMobile: () => window.innerWidth <= 768,
    
    // Detect touch device
    isTouchDevice: () => 'ontouchstart' in window || navigator.maxTouchPoints > 0,
    
    // Get current active section
    getCurrentSection: () => document.querySelector('.section.active')?.id,
    
    // Format number
    formatNumber: (num) => {
        return new Intl.NumberFormat('en-US').format(num);
    }
};

// Export to global scope (if needed)
window.ELLSite = {
    showSection,
    copyCitation,
    utils
};
