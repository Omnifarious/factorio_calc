# Python Factorio Calculator #

This is a simple calculator for the game [Factorio][Factorio].  Since I
like rational numbers and the ratios in the game are usually best
expressed this way, it does all math with fractions from Python's
fractions module.

If you're seeing this on GitHub, I'm a Mercurial user, so this is a
mirror of the actual [repository on bitbucket][bitbucket_repo].

It requires Python 3.6 to work, mostly because I really like `f''`
strings.  I'm also not much of a fancy UI guy, so it just has a bunch of
functions that do the kinds of things I need.

The module is designed to be used like this:

    >>> from fractions import Fraction as F
    >>> import factorio_calc as fc; from factorio calc import item_db as idb
    >>> fc.print_factories(fc.factories_for_each(idb['Yellow Science'], F(1,4), raw_materials=(idb['Circuit'], idb['Copper'], idb['Plastic'], idb['Battery'], idb['Speed Module 1'], idb['Sulfur'], idb['Iron'])))
    Factories   (as a fraction)   Rate      Name
    ---------   ---------------   -------   ---------------------
            2               7/4       1/4   Yellow Science
            4              15/4       3/8   Processing unit
            5               9/2       3/4   Adv Circuit
            2             27/16      27/4   Wire
            1              3/80      15/8   Sulfuric Acid
                                      1/8   Battery
                                        9   Circuit
                                      3/2   Plastic
                                     27/8   Copper
                                     3/16   Sulfur
                                     3/80   Iron
                                     15/4   Water
                                      1/8   Speed Module 1

For items specified as raw materials (or for items that have no
ingredients) it will simply list the rate at which they must be produced
for the given rate. All rates are in items/sec.

I don't print out dependencies because I don't feel it's terribly useful
when building a factory.  You can look at the dependencies in the game
and figure out how to hook things up so that it all works.  What you
really need for planning is an idea of how many of which kinds of
factory you need, and what sorts of supplies you'll need to provide.

For example, in the above build, I have a main bus for the copper,
plastic, circuits, water, and iron.  The rates required for batteries,
sulfur, and speed modules are low enough that I'm comfortable with using
the logistics network to fly them in from other places in my factory
where they're made.  This will yield at least 1 Yellow Science every 4
seconds, and all the fractional factories tell me I will probably get
more production out of it.  I could use the `actual_production` function
to figure out just how much.

[Factorio]: https://www.factorio.com/
[bitbucket_repo]: https://www.bitbucket.org/omnifarious/factorio_calc
