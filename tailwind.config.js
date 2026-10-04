/** Build with: ./tailwindcss -i static/src/input.css -o static/css/app.css --minify */
module.exports = {
  content: ['./templates/**/*.html', './bookings/**/*.py'],
  theme: {
    extend: {},
  },
  plugins: [],
};
