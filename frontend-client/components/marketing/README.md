# Marketing Blocks - Documentation

Ce dossier contient les composants marketing réutilisables extraits du template Sandbox.

## Structure

```
components/marketing/
├── blocks/          # Composants de blocs marketing (Hero, Features, etc.)
├── shared/          # Composants partagés (à venir)
├── sandboxV1.data.ts # Données mock pour la page sandbox-v1
└── README.md        # Ce fichier
```

## Ajouter un nouveau bloc

### 1. Créer le composant

Créer un nouveau fichier dans `blocks/`, par exemple `MyNewBlock.tsx`:

```tsx
interface MyNewBlockProps {
  title: string;
  items: Array<{ name: string; description: string }>;
}

export function MyNewBlock({ title, items }: MyNewBlockProps) {
  return (
    <section className="wrapper !bg-[#ffffff]">
      <div className="container">
        <h2>{title}</h2>
        {items.map((item, index) => (
          <div key={index}>
            <h3>{item.name}</h3>
            <p>{item.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
```

### 2. Ajouter les données dans `sandboxV1.data.ts`

```typescript
export const sandboxV1Data = {
  // ... autres blocs
  myNewBlock: {
    title: 'Mon nouveau bloc',
    items: [
      { name: 'Item 1', description: 'Description 1' },
      { name: 'Item 2', description: 'Description 2' },
    ],
  },
};
```

### 3. Utiliser le bloc dans la page

Dans `app/(marketing)/sandbox-v1/page.tsx`:

```tsx
import { MyNewBlock } from '@/components/marketing/blocks/MyNewBlock';

export default function SandboxV1Page() {
  const { myNewBlock } = sandboxV1Data;
  
  return (
    <div>
      {/* ... autres blocs */}
      <MyNewBlock {...myNewBlock} />
    </div>
  );
}
```

## Classes CSS du template

Les composants utilisent les classes CSS du template Sandbox qui sont chargées dans le layout (`app/(marketing)/sandbox-v1/layout.tsx`):

- `wrapper` - Container principal de section
- `container` - Container avec max-width
- `card` - Carte avec ombre
- `btn`, `btn-yellow` - Boutons stylisés
- Classes Tailwind du template (ex: `!text-[#fab758]`, `xl:!text-[1.9rem]`)

## Assets

Les images et autres assets doivent pointer vers `/theme/assets/...` car ils sont servis depuis `public/theme/assets/`.

## Convention de nommage

- Composants: PascalCase (ex: `Hero.tsx`, `FeaturesGrid.tsx`)
- Fichiers de données: camelCase avec suffix `.data.ts` (ex: `sandboxV1.data.ts`)
- Props interfaces: `ComponentNameProps` (ex: `HeroProps`)

## Exemple complet

Voir les composants existants dans `blocks/` pour des exemples complets avec:
- Structure HTML du template
- Classes CSS appropriées
- Gestion des images avec srcset
- Props typées avec TypeScript


