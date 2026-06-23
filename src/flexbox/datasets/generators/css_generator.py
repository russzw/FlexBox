"""CSS Dataset Generator - produces Tailwind CSS and styling training data."""

import json
from pathlib import Path
from typing import Optional

from ..curator import TrainingExample


SYSTEM_PROMPT = """You are a CSS/Tailwind specialist. Generate responsive, modern styling using:
- Tailwind CSS utility classes
- CSS Grid and Flexbox layouts
- Responsive breakpoints (sm:, md:, lg:, xl:, 2xl:)
- Hover, focus, and active states
- Modern design patterns (glassmorphism, gradients, shadows)
- Clean, maintainable class organization

Output only the code. No explanations."""

CSS_TEMPLATES = [
    # Hero Sections
    {
        "prompt": "Create a hero section with gradient background and CTA",
        "completion": '''<section className="relative min-h-[600px] bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center overflow-hidden">
  <div className="absolute inset-0 bg-black/20" />
  <div className="absolute inset-0">
    <div className="absolute top-20 left-10 w-72 h-72 bg-white/10 rounded-full blur-3xl" />
    <div className="absolute bottom-20 right-10 w-96 h-96 bg-pink-500/20 rounded-full blur-3xl" />
  </div>
  <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
    <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 tracking-tight">
      Build Something
      <span className="block text-transparent bg-clip-text bg-gradient-to-r from-yellow-200 to-pink-200">
        Amazing Today
      </span>
    </h1>
    <p className="text-lg md:text-xl text-white/80 max-w-2xl mx-auto mb-8">
      Create beautiful, responsive websites with our modern toolkit.
    </p>
    <div className="flex flex-col sm:flex-row gap-4 justify-center">
      <button className="px-8 py-3 bg-white text-indigo-600 font-semibold rounded-lg hover:bg-white/90 transition-all hover:scale-105 shadow-lg">
        Get Started
      </button>
      <button className="px-8 py-3 border-2 border-white text-white font-semibold rounded-lg hover:bg-white/10 transition-colors">
        Learn More
      </button>
    </div>
  </div>
</section>''',
    },
    # Card Grid
    {
        "prompt": "Create a responsive card grid with hover effects",
        "completion": '''<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-6">
  {items.map((item) => (
    <div
      key={item.id}
      className="group bg-white rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-100 hover:border-transparent hover:-translate-y-1"
    >
      <div className="relative h-48 overflow-hidden">
        <img
          src={item.image}
          alt={item.title}
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="absolute bottom-4 left-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
          <button className="w-full py-2 bg-white/90 text-gray-900 text-sm font-medium rounded-lg hover:bg-white transition-colors">
            View Details
          </button>
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="px-2 py-0.5 text-xs font-medium bg-indigo-100 text-indigo-700 rounded-full">
            {item.category}
          </span>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-1 group-hover:text-indigo-600 transition-colors">
          {item.title}
        </h3>
        <p className="text-sm text-gray-500 line-clamp-2">{item.description}</p>
      </div>
    </div>
  ))}
</div>''',
    },
    # Navigation
    {
        "prompt": "Create a responsive navigation bar with mobile menu",
        "completion": '''<nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-100">
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div className="flex items-center justify-between h-16">
      <div className="flex-shrink-0">
        <a href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          Logo
        </a>
      </div>
      <div className="hidden md:block">
        <div className="flex items-center gap-1">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
            >
              {link.label}
            </a>
          ))}
        </div>
      </div>
      <div className="hidden md:flex items-center gap-3">
        <button className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors">
          Sign In
        </button>
        <button className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
          Sign Up
        </button>
      </div>
      <button className="md:hidden p-2 text-gray-600 hover:text-gray-900">
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
    </div>
  </div>
</nav>''',
    },
    # Dashboard Layout
    {
        "prompt": "Create a dashboard layout with sidebar and main content area",
        "completion": '''<div className="flex h-screen bg-gray-100">
  <aside className="hidden lg:flex lg:flex-col w-64 bg-white border-r border-gray-200">
    <div className="flex items-center h-16 px-6 border-b border-gray-200">
      <span className="text-xl font-bold text-gray-900">Dashboard</span>
    </div>
    <nav className="flex-1 p-4 space-y-1">
      {navItems.map((item) => (
        <a
          key={item.href}
          href={item.href}
          className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-100 hover:text-gray-900 transition-colors"
        >
          <item.icon className="w-5 h-5" />
          {item.label}
        </a>
      ))}
    </nav>
    <div className="p-4 border-t border-gray-200">
      <div className="flex items-center gap-3">
        <img src="/avatar.jpg" alt="User" className="w-10 h-10 rounded-full" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">John Doe</p>
          <p className="text-xs text-gray-500 truncate">john@example.com</p>
        </div>
      </div>
    </div>
  </aside>
  <main className="flex-1 overflow-auto">
    <header className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
      <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
    </header>
    <div className="p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <p className="text-sm text-gray-500">{stat.name}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
          </div>
        ))}
      </div>
    </div>
  </main>
</div>''',
    },
    # Form Styling
    {
        "prompt": "Style a multi-step form with progress indicator",
        "completion": '''<div className="max-w-2xl mx-auto p-6">
  <div className="flex items-center justify-between mb-8">
    {steps.map((step, idx) => (
      <div key={step.id} className="flex items-center">
        <div
          className={\`flex items-center justify-center w-10 h-10 rounded-full transition-colors \${
            idx < currentStep
              ? 'bg-green-500 text-white'
              : idx === currentStep
              ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
              : 'bg-gray-200 text-gray-500'
          }\`}
        >
          {idx < currentStep ? (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <span className="text-sm font-medium">{idx + 1}</span>
          )}
        </div>
        {idx < steps.length - 1 && (
          <div
            className={\`hidden sm:block w-24 h-1 mx-2 \${
              idx < currentStep ? 'bg-green-500' : 'bg-gray-200'
            }\`}
          />
        )}
      </div>
    ))}
  </div>
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">Full Name</label>
        <input
          type="text"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow"
          placeholder="John Doe"
        />
      </div>
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">Email</label>
        <input
          type="email"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow"
          placeholder="john@example.com"
        />
      </div>
      <div className="flex justify-between pt-4">
        <button
          onClick={prevStep}
          disabled={currentStep === 0}
          className="px-6 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Previous
        </button>
        <button
          onClick={nextStep}
          className="px-6 py-2 text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
        >
          {currentStep === steps.length - 1 ? 'Submit' : 'Next'}
        </button>
      </div>
    </div>
  </div>
</div>''',
    },
    # Pricing Table
    {
        "prompt": "Create a pricing table with three tiers",
        "completion": '''<div className="py-12 bg-gray-50">
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div className="text-center mb-12">
      <h2 className="text-3xl font-bold text-gray-900">Simple, transparent pricing</h2>
      <p className="mt-4 text-lg text-gray-600">Choose the plan that works for you</p>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
      {plans.map((plan) => (
        <div
          key={plan.name}
          className={\`relative flex flex-col p-8 bg-white rounded-2xl shadow-sm border-2 transition-all hover:shadow-lg \${
            plan.featured
              ? 'border-indigo-600 scale-105'
              : 'border-gray-100 hover:border-gray-200'
          }\`}
        >
          {plan.featured && (
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-indigo-600 text-white text-xs font-semibold rounded-full">
              Most Popular
            </span>
          )}
          <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
          <p className="mt-2 text-sm text-gray-500">{plan.description}</p>
          <div className="mt-6">
            <span className="text-4xl font-bold text-gray-900">${plan.price}</span>
            <span className="text-gray-500">/month</span>
          </div>
          <ul className="mt-6 space-y-4 flex-1">
            {plan.features.map((feature) => (
              <li key={feature} className="flex items-center gap-3 text-sm text-gray-600">
                <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {feature}
              </li>
            ))}
          </ul>
          <button
            className={\`mt-8 w-full py-3 px-4 rounded-lg font-medium transition-colors \${
              plan.featured
                ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
            }\`}
          >
            {plan.cta}
          </button>
        </div>
      ))}
    </div>
  </div>
</div>''',
    },
]


class CSSGenerator:
    """Generates CSS/Tailwind training examples."""

    def __init__(self, custom_templates: Optional[list[dict]] = None):
        self.templates = CSS_TEMPLATES.copy()
        if custom_templates:
            self.templates.extend(custom_templates)

    def generate(self) -> list[TrainingExample]:
        """Generate all CSS training examples."""
        examples = []
        
        for template in self.templates:
            example = TrainingExample(
                prompt=template["prompt"],
                completion=template["completion"],
                system_prompt=SYSTEM_PROMPT,
                metadata={"source": "css", "type": "component"},
            )
            examples.append(example)
        
        return examples

    def generate_with_variations(self, multiplier: int = 3) -> list[TrainingExample]:
        """Generate examples with prompt variations."""
        base_examples = self.generate()
        variations = []
        
        prefixes = [
            "Create a responsive",
            "Design a modern",
            "Style a",
            "Build a",
            "Implement a",
        ]
        
        for example in base_examples:
            for i in range(multiplier):
                prefix = prefixes[i % len(prefixes)]
                variation = TrainingExample(
                    prompt=f"{prefix} {example.prompt.lower()}",
                    completion=example.completion,
                    system_prompt=SYSTEM_PROMPT,
                    metadata={
                        "source": "css",
                        "type": "variation",
                        "base_prompt": example.prompt,
                    },
                )
                variations.append(variation)
        
        return base_examples + variations

    def load_from_file(self, filepath: str) -> list[TrainingExample]:
        """Load additional templates from a JSONL file."""
        examples = []
        
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                example = TrainingExample(
                    prompt=data["prompt"],
                    completion=data["completion"],
                    system_prompt=data.get("system_prompt", SYSTEM_PROMPT),
                    metadata={"source": "css", "type": "custom"},
                )
                examples.append(example)
        
        return examples
