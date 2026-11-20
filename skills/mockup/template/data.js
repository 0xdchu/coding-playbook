/* Demo seed for the mockup template. Replace every string with the product's real copy. */
(function (g) {
  const SEED = {
    product: 'Orbit',
    theme: 'light',
    device: 'web',
    generating: false,
    generated: false,
    screens: [
      { id: 'login', title: 'Sign in', group: 'Onboarding', desc: 'Email, one code, then in.' },
      { id: 'board', title: 'Board', group: 'Core loop', desc: 'One brief, steps, then approve.' },
      { id: 'settings', title: 'Settings', group: 'Config', desc: 'Theme and demo data.' }
    ],
    items: [
      { id: 'i1', title: 'Rewrite the landing hero', detail: 'One promise, one proof, one call to action.', status: 'pending' },
      { id: 'i2', title: 'Shoot three product photos', detail: 'Morning light, same table, no props.', status: 'pending' },
      { id: 'i3', title: 'Reply to five comments', detail: 'Answer price and shipping questions first.', status: 'approved' }
    ]
  };
  g.SEED = SEED;
  if (typeof module !== 'undefined') module.exports = SEED;
})(typeof window !== 'undefined' ? window : globalThis);
