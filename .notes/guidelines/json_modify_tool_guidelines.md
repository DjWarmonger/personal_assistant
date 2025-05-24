# JSON Modification Tool Guidelines

## Core Concepts and Requirements

### Value Types and Handling
1. The tool must handle three distinct types of replacements:
	- Direct values (strings, numbers, booleans, etc.)
	- JSON structures (arrays and objects)
	- Lambda functions for transformations

2. String Handling Requirements:
	- Plain strings (e.g., "1") must remain strings
	- JSON strings must only be parsed if they represent arrays or objects
	- Lambda strings must be evaluated as functions

### Lambda Function Validation

#### Key Learnings from Implementation
1. Initial Overcomplication:
	- We initially over-validated lambda functions
	- Tried to catch runtime errors during validation
	- Attempted to validate undefined names
	- These attempts led to confusing error messages and brittle code

2. Better Approach:
	- Only validate syntax during evaluation
	- Let runtime errors occur naturally during execution
	- Provide clear error context when the error occurs
	- Separate validation errors from execution errors

#### Validation Guidelines
1. During Lambda Evaluation:
	- Check if string starts with "lambda"
	- Validate syntax using compile()
	- Verify the result is callable
	- DO NOT attempt to catch runtime errors
	- DO NOT try to validate undefined names
	- DO NOT test execution with sample values

2. During Execution:
	- Catch and wrap execution errors with context
	- Include the value that caused the error
	- Maintain original error message clarity

### Error Handling - Best Practices

1. Error Message Structure:
	- Validation errors: "Invalid lambda expression: {syntax_error}"
	- Execution errors: "Failed to apply replacement to value '{value}': {error}"
	- Avoid wrapping errors multiple times
	- Keep original error messages visible

2. Error Categories:
	- Syntax Errors: Invalid lambda syntax
	- Type Errors: Invalid operations on values
	- Name Errors: Undefined functions/variables
	- JSON Parse Errors: Invalid JSON strings

## Testing Guidelines

1. Test Categories:
	- Direct value replacements (strings, numbers, etc.)
	- JSON structure replacements (arrays, objects)
	- Lambda transformations (successful cases)
	- Error cases (syntax, runtime, type errors)

2. Test Cases Must Cover:
	- String-to-string replacements (verify no type conversion)
	- JSON array/object parsing
	- Lambda syntax validation
	- Lambda execution errors
	- Edge cases in value types

## Common Pitfalls

1. Type Conversion Issues:
	- JSON parsing can convert strings to numbers/booleans
	- Always verify string values remain strings
	- Check type preservation in tests

2. Error Handling:
	- Avoid nested try-except blocks that wrap errors multiple times
	- Don't catch errors too early in the validation phase
	- Let runtime errors happen naturally

3. Validation Scope:
	- Don't try to catch runtime errors during validation
	- Focus validation on syntax and basic callable checks
	- Separate validation from execution concerns

## Future Improvements

1. Documentation:
	- Clear examples for each type of replacement
	- Error message reference
	- Common patterns and anti-patterns

2. Error Messages:
	- Standardize error message formats
	- Include context without nesting
	- Keep original error details visible

3. Testing:
	- Separate test files by functionality
	- Clear test case names
	- Comprehensive edge cases

## Implementation Checklist

When implementing similar tools:

1. Value Types:
	- [ ] Define all supported value types
	- [ ] Document type handling behavior
	- [ ] Implement type-specific validation

2. Validation:
	- [ ] Keep validation minimal and focused
	- [ ] Separate validation from execution
	- [ ] Clear validation error messages

3. Error Handling:
	- [ ] Define error categories
	- [ ] Structure error messages
	- [ ] Avoid error message wrapping

4. Testing:
	- [ ] Cover all value types
	- [ ] Test error conditions
	- [ ] Verify type preservation
	- [ ] Include edge cases 