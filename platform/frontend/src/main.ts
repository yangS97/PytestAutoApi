import { createApp } from 'vue';
import { createPinia } from 'pinia';

import App from './App.vue';
import router from './router';

import '@/styles/variables.css';
import '@/styles/base.css';

const app = createApp(App);
const pinia = createPinia();

// 这里先挂载 Pinia，再挂载路由。
// 原因是路由守卫里会读取 store；如果顺序反了，首次导航时 store 还没准备好。
app.use(pinia);
app.use(router);
app.mount('#app');

