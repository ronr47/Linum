module.exports = grammar({
  name: 'linum',

  rules: {
    source_file: $ => repeat($._statement),

    _statement: $ => choice(
      $.let_binding,
      $.return_statement,
      $.block
    ),

    let_binding: $ => seq(
      'let',
      field('name', $.identifier),
      ':',
      field('type', $.type_specifier),
      '=',
      field('value', $._expression),
      ';'
    ),

    return_statement: $ => seq('return', $._expression, ';'),

    block: $ => seq('{', repeat($._statement), '}'),

    _expression: $ => choice(
      $.identifier,
      $.literal_register,
      $.binary_op
    ),

    binary_op: $ => prec.left(1, seq(
      $._expression,
      choice('+', '-', '*', '/'),
      $._expression
    )),

    literal_register: $ => seq('%', choice('val_42', 'uninit_stub', /[a-zA-Z0-9_]+/)),
    type_specifier: $ => choice('ptr', 'COPY', 'i32', 'f64'),
    identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,
  }
});
