import { BrowserRouter } from 'react-router'

import { Providers } from '@/app/providers'
import { AppRouter } from '@/app/router'

export function App() {
  return (
    <Providers>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </Providers>
  )
}
