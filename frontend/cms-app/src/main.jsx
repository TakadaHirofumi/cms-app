/**
 * Reactアプリ起動
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'


// HTMLのrootにReactアプリを描画、StrictModeで開発時の問題検出を補助
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
