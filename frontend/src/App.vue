<template>
  <div id="app">
    <MdEditor />
  </div>
</template>

<script>
import MdEditor from './components/MdEditor.vue'

export default {
  name: 'App',
  components: {
    MdEditor
  }
}
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  overflow: hidden;
}
</style>
