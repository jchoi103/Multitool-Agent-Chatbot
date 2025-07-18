import { Product } from '../types';

export const exampleProducts: Product[] = [
  {
    id: 'agx-123',
    productName: 'Awesome Gadget X',
    description: "The most awesome gadget you'll ever own.",
    image: '/src/assets/chatbot.png',
    category: 'Electronics',
    variants: [
      {
        sku: 'AGX-001',
        price: 99.99,
        weight: 0.5,
        length: 10,
        width: 5,
        stock: 50,
      },
      {
        sku: 'AGX-002',
        price: 109.99,
        weight: 0.6,
        length: 10,
        width: 5,
        stock: 30,
      },
    ],
  },
  {
    id: 'swy-456',
    productName: 'Super Widget Y',
    description: 'A super widget for all your widgeting needs.',
    image: '/src/assets/chatbox.svg',
    category: 'Widgets',
    variants: [
      {
        sku: 'SWY-001',
        price: 49.5,
        weight: 0.2,
        length: 5,
        width: 5,
        stock: 100,
      },
    ],
  },
  {
    id: 'hfz-789',
    productName: 'Hyper Flux Z',
    description: 'It fluxes hyperly!',
    image: '/src/assets/chatbot.png',
    category: 'Flux Capacitors',
    variants: [
      {
        sku: 'HFZ-001',
        price: 1999.0,
        weight: 2.5,
        length: 20,
        width: 15,
        stock: 5,
      },
    ],
  },
  {
    id: 'example-alpha-001',
    productName: 'Example Gadget Alpha',
    description: 'This is a fantastic example gadget with many features.',
    image: '/src/assets/react.svg',
    category: 'Examples',
    variants: [
      {
        sku: 'EX-ALPHA-001',
        price: 19.99,
        stock: 150,
        weight: 0.3,
        length: 8,
        width: 4,
      },
    ],
  },
];
