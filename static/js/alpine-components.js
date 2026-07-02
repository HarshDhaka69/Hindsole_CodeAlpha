document.addEventListener("alpine:init", () => {
  // Lightweight x-intersect directive (we don't pull in the full Alpine
  // Intersect plugin bundle just for one use case: scroll-triggered
  // fade-ins on product cards). Usage: x-intersect.once="..."
  Alpine.directive("intersect", (el, { expression, modifiers }, { evaluate }) => {
    const once = modifiers.includes("once");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            evaluate(expression);
            if (once) observer.unobserve(el);
          }
        });
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
  });
});

// Lets any element dispatch `open-mini-cart` and have the root x-data
// (which owns `miniCartOpen`) react, even from deeply nested HTMX-swapped
// fragments where direct Alpine scope access isn't available.
document.addEventListener("open-mini-cart", () => {
  const root = document.body;
  if (root && root._x_dataStack && root._x_dataStack.length) {
    root._x_dataStack[0].miniCartOpen = true;
  }
});
