#ifndef EXAMPLE_CONCEPTS_GROUPED_H
#define EXAMPLE_CONCEPTS_GROUPED_H

#include <type_traits>
#include <concepts>
#include <string>
#include <iterator>

/**
 * @defgroup type_concepts Type Concepts
 * @brief Concepts related to type properties
 * @details This group contains concepts that constrain template parameters
 * based on type properties like arithmetic, integral, etc.
 */

/**
 * @defgroup iterator_concepts Iterator and Range Concepts
 * @brief Concepts related to iterators and ranges
 * @details This group contains concepts that constrain template parameters
 * based on iterator and range capabilities.
 */

/**
 * @defgroup string_concepts String Concepts
 * @brief Concepts related to string-like types
 * @details This group contains concepts for types that behave like strings.
 * @ingroup type_concepts
 */

// ---- Type Concepts (top-level group) ----

/**
 * @ingroup type_concepts
 * @brief Concept checking if a type is an arithmetic type.
 * @tparam T The type to check
 */
template <typename T>
concept IsArithmetic = std::is_arithmetic_v<T>;

/**
 * @ingroup type_concepts
 * @brief Concept checking if a type is an integral type.
 * @tparam T The type to check
 */
template <typename T>
concept IsIntegral = std::integral<T>;

/**
 * @ingroup type_concepts
 * @brief Concept checking if a type is a floating point type.
 * @tparam T The type to check
 */
template <typename T>
concept IsFloatingPoint = std::floating_point<T>;

/**
 * @ingroup type_concepts
 * @brief Concept checking if a type is default constructible.
 * @tparam T The type to check
 */
template <typename T>
concept IsDefaultConstructible = std::is_default_constructible_v<T>;

// ---- Iterator and Range Concepts (top-level group) ----

/**
 * @ingroup iterator_concepts
 * @brief Concept checking if a type is an input iterator.
 * @tparam T The type to check
 */
template <typename T>
concept IsInputIterator = std::input_iterator<T>;

/**
 * @ingroup iterator_concepts
 * @brief Concept checking if a type is a forward iterator.
 * @tparam T The type to check
 */
template <typename T>
concept IsForwardIterator = std::forward_iterator<T>;

/**
 * @ingroup iterator_concepts
 * @brief Concept checking if a type is a random access iterator.
 * @tparam T The type to check
 */
template <typename T>
concept IsRandomAccessIterator = std::random_access_iterator<T>;

// ---- String Concepts (subgroup of type_concepts) ----

/**
 * @ingroup string_concepts
 * @brief Concept checking if a type is convertible to std::string.
 * @tparam T The type to check
 */
template <typename T>
concept StringConvertible = std::convertible_to<T, std::string>;

/**
 * @ingroup string_concepts
 * @brief Concept checking if a type has a c_str() method.
 * @tparam T The type to check
 */
template <typename T>
concept HasCStr = requires(T t) {
    { t.c_str() } -> std::convertible_to<const char*>;
};

#endif // EXAMPLE_CONCEPTS_GROUPED_H
