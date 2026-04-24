#ifndef EXAMPLE_CONCEPTS_NAMESPACED_H
#define EXAMPLE_CONCEPTS_NAMESPACED_H

#include <concepts>
#include <string>
#include <type_traits>

/**
 * @namespace geometry
 * @brief Namespace for geometric concepts and types.
 */
namespace geometry {

/**
 * @brief Concept that checks if a type is Drawable.
 * @details Requires a draw() method returning void.
 * @tparam T The type to check
 */
template <typename T>
concept Drawable = requires(T a) {
    { a.draw() } -> std::same_as<void>;
};

/**
 * @brief Concept that checks if a type is Measurable.
 * @details Requires an area() method returning a numeric type.
 * @tparam T The type to check
 */
template <typename T>
concept Measurable = requires(T a) {
    { a.area() } -> std::convertible_to<double>;
};

/**
 * @brief Render a drawable object.
 * @tparam T A Drawable type
 * @param obj The object to render
 */
template <Drawable T>
void render(const T& obj) {
    obj.draw();
}

} // namespace geometry

/**
 * @namespace audio
 * @brief Namespace for audio-related concepts and types.
 */
namespace audio {

/**
 * @brief Concept that checks if a type is Drawable (in audio context: renderable waveform).
 * @details Requires a draw() method returning void — same name as geometry::Drawable
 * but different semantic meaning.
 * @tparam T The type to check
 */
template <typename T>
concept Drawable = requires(T a) {
    { a.draw() } -> std::same_as<void>;
    { a.sampleRate() } -> std::convertible_to<int>;
};

/**
 * @brief Concept that checks if a type is Measurable (in audio context: measurable duration).
 * @details Requires a duration() method — same name as geometry::Measurable
 * but completely different constraints.
 * @tparam T The type to check
 */
template <typename T>
concept Measurable = requires(T a) {
    { a.duration() } -> std::convertible_to<double>;
};

/**
 * @brief Render an audio waveform.
 * @tparam T A Drawable audio type
 * @param obj The audio object to render
 */
template <Drawable T>
void render(const T& obj) {
    obj.draw();
}

} // namespace audio

#endif // EXAMPLE_CONCEPTS_NAMESPACED_H
